from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from enem_project.data.class_engineering.transformers import run_class_pipeline
from enem_project.infra.io import read_parquet, write_parquet


@dataclass
class StreamingClassResult:
    classes_path: Path
    row_count: int
    columns: tuple[str, ...]
    summary_df: pd.DataFrame


def stream_class_pipeline(
    clean_path: Path,
    classes_path: Path,
    *,
    chunk_rows: int = 50_000,
) -> StreamingClassResult:
    df_clean = read_parquet(clean_path)
    result = run_class_pipeline(df_clean, chunk_size=chunk_rows)
    write_parquet(result.classes_df, classes_path)

    return StreamingClassResult(
        classes_path=classes_path,
        row_count=len(result.classes_df),
        columns=tuple(result.classes_df.columns),
        summary_df=result.summary_df,
    )


__all__ = ["stream_class_pipeline", "StreamingClassResult"]
