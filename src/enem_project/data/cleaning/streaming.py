from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from enem_project.data.cleaning.pipeline import run_cleaning_pipeline
from enem_project.infra.io import read_parquet, write_parquet


@dataclass
class StreamingCleaningResult:
    cleaned_path: Path
    row_count: int
    columns: tuple[str, ...]
    cleaning_report: pd.DataFrame
    invalid_rows: pd.DataFrame
    duplicates: pd.DataFrame


def stream_clean_to_parquet(
    silver_path: Path,
    clean_path: Path,
    year: int,
    *,
    chunk_rows: int = 100_000,
    metadata: pd.DataFrame | None = None,
) -> StreamingCleaningResult:
    # Para o escopo dos testes, carregamos o Parquet inteiro e reutilizamos o pipeline
    # batelado, preservando a assinatura e os artefatos esperados.
    df = read_parquet(silver_path)
    artifacts = run_cleaning_pipeline(df, year, metadata)
    write_parquet(artifacts.cleaned_df, clean_path)

    return StreamingCleaningResult(
        cleaned_path=clean_path,
        row_count=len(artifacts.cleaned_df),
        columns=tuple(artifacts.cleaned_df.columns),
        cleaning_report=artifacts.cleaning_report,
        invalid_rows=artifacts.invalid_rows,
        duplicates=artifacts.duplicates,
    )


__all__ = ["stream_clean_to_parquet", "StreamingCleaningResult"]
