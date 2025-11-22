from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from enem_project.data.metadata import filter_metadata_for_year, load_metadata
from enem_project.infra.logging import logger


@dataclass
class CleaningArtifacts:
    cleaned_df: pd.DataFrame
    cleaning_report: pd.DataFrame
    invalid_rows: pd.DataFrame
    duplicates: pd.DataFrame


def _validate_numeric_ranges(df: pd.DataFrame) -> pd.Series:
    invalid_age = pd.Series(False, index=df.index)
    if "NU_IDADE" in df.columns:
        invalid_age = (df["NU_IDADE"] < 10) | (df["NU_IDADE"] > 150)

    nota_cols = [c for c in df.columns if c.startswith("NOTA_")]
    invalid_notas = pd.Series(False, index=df.index)
    if nota_cols:
        invalid_notas = False
        for col in nota_cols:
            invalid_notas = invalid_notas | (df[col] < 0) | (df[col] > 1000)
    return invalid_age | invalid_notas


def _apply_domains(df: pd.DataFrame, metadata: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_out = df.copy()
    domain_fixes = []
    for _, row in metadata.iterrows():
        col = row.get("nome_padrao") or row.get("nome_original")
        domain = row.get("dominio_valores")
        if col in df_out.columns and isinstance(domain, Iterable):
            valid_values = set(domain)
            mask_invalid = ~df_out[col].isin(valid_values)
            if mask_invalid.any():
                df_out.loc[mask_invalid, col] = "UNKNOWN"
                domain_fixes.append({"column": col, "affected_rows": int(mask_invalid.sum())})
    domain_report = pd.DataFrame(domain_fixes)
    return df_out, domain_report


def run_cleaning_pipeline(df: pd.DataFrame, year: int, metadata: pd.DataFrame | None = None) -> CleaningArtifacts:
    if metadata is None:
        try:
            metadata = load_metadata()
        except FileNotFoundError:
            metadata = pd.DataFrame()

    metadata_year = filter_metadata_for_year(metadata, year) if metadata is not None else pd.DataFrame()

    invalid_mask = _validate_numeric_ranges(df)
    invalid_rows = df[invalid_mask].copy()
    df_valid = df[~invalid_mask].copy()

    # Remove duplicados mantendo a primeira ocorrência
    duplicates = pd.DataFrame()
    if "ID_INSCRICAO" in df_valid.columns:
        duplicate_mask = df_valid.duplicated(subset=["ID_INSCRICAO"], keep="first")
        duplicates = df_valid[duplicate_mask].copy()
        df_valid = df_valid[~duplicate_mask]

    df_corrected, domain_report = _apply_domains(df_valid, metadata_year)

    cleaning_steps = []
    if not invalid_rows.empty:
        cleaning_steps.append({"rule": "invalid_rows", "affected_rows": len(invalid_rows)})
    if not duplicates.empty:
        cleaning_steps.append({"rule": "duplicates", "affected_rows": len(duplicates)})
    if not domain_report.empty:
        cleaning_steps.extend(
            {"rule": f"domain:{row['column']}", "affected_rows": row["affected_rows"]}
            for _, row in domain_report.iterrows()
        )

    cleaning_report = pd.DataFrame(cleaning_steps)
    logger.info(
        "Limpeza concluída para %s: %d válidos, %d inválidos, %d duplicados.",
        year,
        len(df_corrected),
        len(invalid_rows),
        len(duplicates),
    )

    return CleaningArtifacts(
        cleaned_df=df_corrected.reset_index(drop=True),
        cleaning_report=cleaning_report.reset_index(drop=True),
        invalid_rows=invalid_rows.reset_index(drop=True),
        duplicates=duplicates.reset_index(drop=True),
    )


__all__ = ["run_cleaning_pipeline", "CleaningArtifacts"]
