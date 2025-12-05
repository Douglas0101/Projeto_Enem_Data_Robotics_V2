from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from enem_project.data.metadata import filter_metadata_for_year, load_metadata
from enem_project.data.cleaning.rules import DEFAULT_NUMERIC_RULES
from enem_project.infra.logging import logger


@dataclass
class CleaningArtifacts:
    cleaned_df: pd.DataFrame
    cleaning_report: pd.DataFrame
    invalid_rows: pd.DataFrame
    duplicates: pd.DataFrame


def _validate_numeric_ranges(df: pd.DataFrame) -> pd.Series:
    """
    Valida faixas numéricas conforme regras definidas em rules.py.
    Ignora valores nulos (NaN) para não descartar dados históricos incompletos.
    Marca como inválida a linha que tiver valor PRESENTE fora do intervalo.
    """
    invalid_mask = pd.Series(False, index=df.index)

    for rule in DEFAULT_NUMERIC_RULES:
        col = rule.column
        if col not in df.columns:
            continue

        # Obtém a série numérica
        series = pd.to_numeric(df[col], errors="coerce")

        # Apenas verifica onde NÃO é nulo
        not_na = series.notna()

        # Condição de falha: valor < min OU valor > max
        rule_violation = pd.Series(False, index=df.index)

        if rule.min_value is not None:
            rule_violation |= series < rule.min_value

        if rule.max_value is not None:
            rule_violation |= series > rule.max_value

        # Atualiza a máscara global de invalidez
        # Linha é inválida se violar a regra E não for nula
        invalid_mask |= rule_violation & not_na

    return invalid_mask


def _apply_domains(
    df: pd.DataFrame, metadata: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_out = df.copy()
    domain_fixes = []

    # Colunas que têm domínio definido
    cols_with_domain = metadata.dropna(subset=["dominio_valores"])

    for _, row in cols_with_domain.iterrows():
        col = row["nome_padrao"]
        domain = row["dominio_valores"]

        if col in df_out.columns and domain is not None:
            # domain vem como numpy array ou lista do parquet
            valid_values = set(domain)

            # Verifica valores fora do domínio
            mask_invalid = ~df_out[col].isin(valid_values) & df_out[col].notna()

            if mask_invalid.any():
                # Decide o valor de substituição baseado no tipo da coluna
                if pd.api.types.is_numeric_dtype(df_out[col]):
                    replacement = pd.NA
                else:
                    replacement = "UNKNOWN"

                df_out.loc[mask_invalid, col] = replacement

                domain_fixes.append(
                    {"column": col, "affected_rows": int(mask_invalid.sum())}
                )

    domain_report = pd.DataFrame(domain_fixes)
    return df_out, domain_report


def run_cleaning_pipeline(
    df: pd.DataFrame, year: int, metadata: pd.DataFrame | None = None
) -> CleaningArtifacts:
    if metadata is None:
        try:
            metadata = load_metadata()
        except FileNotFoundError:
            metadata = pd.DataFrame()

    metadata_year = (
        filter_metadata_for_year(metadata, year)
        if metadata is not None
        else pd.DataFrame()
    )

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
        cleaning_steps.append(
            {"rule": "invalid_rows", "affected_rows": len(invalid_rows)}
        )
    if not duplicates.empty:
        cleaning_steps.append({"rule": "duplicates", "affected_rows": len(duplicates)})
    if not domain_report.empty:
        cleaning_steps.extend(
            {"rule": f"domain:{row['column']}", "affected_rows": row["affected_rows"]}
            for _, row in domain_report.iterrows()
        )

    cleaning_report = pd.DataFrame(cleaning_steps)
    logger.info(
        "Limpeza concluída para {}: {} válidos, {} inválidos, {} duplicados.",
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
