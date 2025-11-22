from __future__ import annotations

import os
from pathlib import Path

import os
from pathlib import Path

import pandas as pd

from ..base import Agent
from ..context import DataHandle, DatasetArtifact, OrchestratorContext
from ...config import paths
from ...config.hardware import PROFILE
from ...data.cleaning.pipeline import run_cleaning_pipeline
from ...data.cleaning.streaming import StreamingCleaningResult, stream_clean_to_parquet
from ...data.metadata import load_metadata
from ...infra.logging import logger
from ...infra.io import read_parquet, write_parquet


class CleanseAgent(Agent):
    """
    Executa a limpeza avançada sobre a camada silver e persiste resultados na camada gold.
    """

    def __init__(self, year: int):
        self.year = int(year)
        self.name = f"cleaning-{year}"
        self.allowed_sensitivity_read = ["SENSITIVE", "AGGREGATED"]
        self.allowed_sensitivity_write = ["AGGREGATED"]

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        silver_path = paths.silver_dir() / f"microdados_enem_{self.year}.parquet"
        if not silver_path.exists():
            raise FileNotFoundError(silver_path)

        logger.info("[%s] Iniciando limpeza avançada: %s", self.name, silver_path)
        metadata = load_metadata()

        clean_dir = paths.gold_dir() / "cleaned"
        clean_dir.mkdir(parents=True, exist_ok=True)
        clean_path = clean_dir / f"microdados_enem_{self.year}_clean.parquet"

        if _should_stream_cleaning(silver_path):
            chunk_rows = _resolve_cleaning_chunk_rows()
            logger.info(
                "[%s] Streaming habilitado para limpeza (%s, chunk=%d).",
                self.name,
                _format_size_gb(silver_path),
                chunk_rows,
            )
            streaming_result = _run_streaming_cleaning(
                silver_path,
                clean_path,
                self.year,
                chunk_rows,
                metadata,
            )
            clean_path = streaming_result.cleaned_path
            clean_df = None
            cleaning_report = streaming_result.cleaning_report
            invalid_rows = streaming_result.invalid_rows
            duplicates = streaming_result.duplicates
            row_count = streaming_result.row_count
            columns = streaming_result.columns
        else:
            df = read_parquet(silver_path)
            artifacts = run_cleaning_pipeline(df, self.year, metadata)
            clean_df = artifacts.cleaned_df
            cleaning_report = artifacts.cleaning_report
            invalid_rows = artifacts.invalid_rows
            duplicates = artifacts.duplicates
            row_count = len(clean_df)
            columns = tuple(clean_df.columns)

        if clean_df is not None:
            write_parquet(clean_df, clean_path)

        report_dir = paths.gold_dir() / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(cleaning_report, pd.DataFrame) and not cleaning_report.empty:
            write_parquet(
                cleaning_report,
                report_dir / f"cleaning_report_{self.year}.parquet",
            )
        if isinstance(invalid_rows, pd.DataFrame) and not invalid_rows.empty:
            write_parquet(
                invalid_rows,
                report_dir / f"cleaning_invalid_{self.year}.parquet",
            )
        if isinstance(duplicates, pd.DataFrame) and not duplicates.empty:
            write_parquet(
                duplicates,
                report_dir / f"cleaning_duplicates_{self.year}.parquet",
            )

        artifact = DatasetArtifact(
            path=clean_path,
            row_count=row_count,
            columns=columns,
        )
        ctx.add_data(
            f"clean_{self.year}",
            DataHandle(
                name=f"clean_{self.year}",
                sensitivity="AGGREGATED",
                payload=artifact,
            ),
        )
        ctx.add_log(f"{self.name}: {row_count} linhas limpas.")
        logger.success(
            "[%s] Limpeza concluída (%d linhas).",
            self.name,
            row_count,
        )
        return ctx


def _resolve_cleaning_chunk_rows() -> int:
    env_value = os.getenv("ENEM_CLEANING_CHUNK_ROWS")
    if env_value:
        try:
            value = int(env_value)
            if value > 0:
                return value
        except ValueError:
            pass
    return max(100_000, PROFILE.csv_chunk_rows // 2)


def _cleaning_threshold_gb() -> float:
    env_value = os.getenv("ENEM_CLEANING_STREAMING_GB")
    if env_value:
        try:
            value = float(env_value)
            if value > 0:
                return value
        except ValueError:
            pass
    # Fallback mais conservador para Parquet: arquivos limpos acima de
    # ~150 MB passam a usar streaming por padrão, reduzindo picos de RAM
    # em anos com muitos registros (2001+).
    return min(PROFILE.streaming_threshold_gb / 2, 0.15)


def _should_stream_cleaning(path: Path) -> bool:
    force = os.getenv("ENEM_FORCE_CLEANING_STREAMING", "")
    if force.strip().lower() in {"1", "true", "yes", "y"}:
        return True
    size_gb = _file_size_gb(path)
    return size_gb >= _cleaning_threshold_gb()


def _file_size_gb(path: Path) -> float:
    try:
        return path.stat().st_size / (1024**3)
    except FileNotFoundError:
        return 0.0


def _format_size_gb(path: Path) -> str:
    return f"{_file_size_gb(path):.2f} GB"


def _run_streaming_cleaning(
    silver_path: Path,
    clean_path: Path,
    year: int,
    chunk_rows: int,
    metadata: pd.DataFrame,
) -> StreamingCleaningResult:
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    return stream_clean_to_parquet(
        silver_path,
        clean_path,
        year,
        chunk_rows=chunk_rows,
        metadata=metadata,
    )
