from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import pandas as pd


@dataclass
class ClassPipelineResult:
    classes_df: pd.DataFrame
    summary_df: pd.DataFrame


def apply_class_definitions(
    df: pd.DataFrame, definitions: Iterable[Callable[[pd.DataFrame], pd.Series]]
) -> pd.DataFrame:
    output = df.copy()
    for func in definitions:
        series = func(output)
        output[series.name] = series
    return output


def _class_faixa_etaria(df: pd.DataFrame) -> pd.Series:
    idade = df.get("NU_IDADE", pd.Series([], dtype=float))
    bins = [0, 17, 24, 34, 200]
    labels = ["ATE_17", "18_A_24", "25_A_34", "35_MAIS"]
    return pd.cut(idade, bins=bins, labels=labels, include_lowest=True).rename(
        "CLASS_FAIXA_ETARIA"
    )


def _class_nota_global(df: pd.DataFrame) -> pd.Series:
    notas = df[[c for c in df.columns if c.startswith("NOTA_")]]
    media = notas.mean(axis=1)

    def _classify(value: float) -> str:
        if pd.isna(value):
            return "NA"
        if value >= 650:
            return "ALTA"
        if value >= 550:
            return "MEDIA"
        return "BAIXA"

    labels = media.map(_classify)
    return labels.rename("CLASS_NOTA_GLOBAL")


def _class_renda(df: pd.DataFrame) -> pd.Series:
    renda = df.get("RENDA_FAMILIAR", pd.Series([], dtype=object)).fillna("UNKNOWN")
    mapping = {"A": "A", "B": "B", "C": "C", "UNKNOWN": "UNKNOWN"}
    return renda.map(lambda v: mapping.get(v, "UNKNOWN")).rename("CLASS_RENDA_FAMILIAR")


def _build_summary(df: pd.DataFrame, class_columns: list[str]) -> pd.DataFrame:
    records = []
    for col in class_columns:
        counts = df[col].value_counts(dropna=False)
        for value, total in counts.items():
            records.append(
                {"class_name": col, "class_value": str(value), "total": int(total)}
            )
    return pd.DataFrame(records)


def run_class_pipeline(
    df: pd.DataFrame, *, chunk_size: int = 100_000
) -> ClassPipelineResult:
    definitions = [_class_faixa_etaria, _class_nota_global, _class_renda]
    chunks = []
    class_columns = ["CLASS_FAIXA_ETARIA", "CLASS_NOTA_GLOBAL", "CLASS_RENDA_FAMILIAR"]

    for start in range(0, len(df), max(1, chunk_size)):
        end = start + max(1, chunk_size)
        chunk = df.iloc[start:end]
        transformed = apply_class_definitions(chunk, definitions)
        chunks.append(transformed)

    classes_df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    summary_df = _build_summary(classes_df, class_columns)
    return ClassPipelineResult(classes_df=classes_df, summary_df=summary_df)


__all__ = ["run_class_pipeline", "apply_class_definitions", "ClassPipelineResult"]
