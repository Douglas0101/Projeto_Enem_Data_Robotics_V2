from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from ..base import Agent
from ..context import DataHandle, DatasetArtifact, OrchestratorContext
from ...config import paths
from ...config.hardware import PROFILE
from ...data.class_engineering.transformers import run_class_pipeline
from ...data.class_engineering.streaming import StreamingClassResult, stream_class_pipeline
from ...infra.logging import logger
from ...infra.io import read_parquet, write_parquet


class ClassEngineeringAgent(Agent):
    """
    Constrói classes analíticas/socioeconômicas a partir do dataset limpo.
    """

    def __init__(self, year: int):
        self.year = int(year)
        self.name = f"class-engineering-{year}"
        self.allowed_sensitivity_read = ["AGGREGATED"]
        self.allowed_sensitivity_write = ["AGGREGATED"]

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        handle_key = f"clean_{self.year}"
        handle = ctx.get_data(handle_key)
        payload = handle.payload
        if not isinstance(payload, DatasetArtifact):
            raise TypeError(f"Payload inválido para {handle_key}: {type(payload)}")

        logger.info("[%s] Gerando classes para %s", self.name, payload.path)
        classes_dir = paths.gold_dir() / "classes"
        classes_dir.mkdir(parents=True, exist_ok=True)
        classes_path = classes_dir / f"classes_enem_{self.year}.parquet"
        summary_path = classes_dir / f"classes_summary_{self.year}.parquet"

        chunk_size = _resolve_class_chunk_rows()
        use_streaming = _should_stream_classes(payload.path, payload.row_count)

        if use_streaming:
            logger.info(
                "[%s] Streaming de classes ativado (%s, chunk=%d).",
                self.name,
                _format_size_gb(payload.path),
                chunk_size,
            )
            streaming_result = stream_class_pipeline(
                payload.path,
                classes_path,
                chunk_rows=chunk_size,
            )
            classes_df = None
            summary_df = streaming_result.summary_df
            row_count = streaming_result.row_count
            columns = streaming_result.columns
        else:
            df_clean = read_parquet(payload.path)
            logger.info(
                "[%s] Perfil de hardware → processamento em lotes de até %d linhas.",
                self.name,
                chunk_size,
            )
            result = run_class_pipeline(df_clean, chunk_size=chunk_size)
            classes_df = result.classes_df
            summary_df = result.summary_df
            row_count = len(result.classes_df)
            columns = tuple(result.classes_df.columns)

        if classes_df is not None:
            write_parquet(classes_df, classes_path)

        if isinstance(summary_df, pd.DataFrame) and not summary_df.empty:
            write_parquet(summary_df, summary_path)

        artifact = DatasetArtifact(
            path=classes_path,
            row_count=row_count,
            columns=columns,
        )
        ctx.add_data(
            f"classes_{self.year}",
            DataHandle(
                name=f"classes_{self.year}",
                sensitivity="AGGREGATED",
                payload=artifact,
            ),
        )
        ctx.add_log(f"{self.name}: classes geradas e salvas em {classes_path.name}.")
        logger.success(
            "[%s] Classes concluídas (%d linhas).",
            self.name,
            row_count,
        )
        return ctx


def _resolve_class_chunk_rows() -> int:
    env_value = os.getenv("ENEM_CLASS_CHUNK_ROWS")
    if env_value:
        try:
            value = int(env_value)
            if value > 0:
                return value
        except ValueError:
            pass
    return max(50_000, PROFILE.csv_chunk_rows // 3)


def _class_streaming_threshold_gb() -> float:
    env_value = os.getenv("ENEM_CLASS_STREAMING_GB")
    if env_value:
        try:
            value = float(env_value)
            if value > 0:
                return value
        except ValueError:
            pass
    return PROFILE.streaming_threshold_gb / 3


def _should_stream_classes(clean_path: Path, row_count: int | None = None) -> bool:
    force = os.getenv("ENEM_FORCE_CLASS_STREAMING", "")
    if force.strip().lower() in {"1", "true", "yes", "y"}:
        return True

    if row_count is not None:
        # Para datasets limpos com muitas linhas, processamos em modo streaming
        # independentemente do tamanho em disco, pois a engenharia de classes
        # tende a multiplicar o uso de RAM.
        row_threshold = max(300_000, PROFILE.csv_chunk_rows // 2)
        if row_count >= row_threshold:
            return True

    return _file_size_gb(clean_path) >= _class_streaming_threshold_gb()


def _file_size_gb(path: Path) -> float:
    try:
        return path.stat().st_size / (1024**3)
    except FileNotFoundError:
        return 0.0


def _format_size_gb(path: Path) -> str:
    return f"{_file_size_gb(path):.2f} GB"
