from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow.parquet as pq

from ...config import paths
from ...data import metadata as metadata_module
from ...infra.logging import logger
from ...infra.io import write_parquet
from ..base import Agent
from ..context import DataHandle, OrchestratorContext


def _parquet_overview(path: Path) -> tuple[int, list[str]]:
    """
    Retorna contagem de linhas e lista de colunas sem carregar o dataset
    completo em memória.
    """
    pq_file = pq.ParquetFile(path)
    row_count = int(pq_file.metadata.num_rows)
    columns = list(pq_file.schema.names)
    return row_count, columns


@dataclass
class ParquetQualityResult:
    layer: str
    parquet_path: str
    row_count: int
    column_count: int
    column_sample: list[str]
    year: int | None = None
    has_ano_column: bool | None = None
    missing_expected_columns: list[str] | None = None
    columns_not_in_metadata: list[str] | None = None
    notes: str | None = None

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "layer": self.layer,
                    "ano": self.year,
                    "parquet_path": self.parquet_path,
                    "row_count": self.row_count,
                    "column_count": self.column_count,
                    "has_ano_column": self.has_ano_column,
                    "missing_expected_columns": self.missing_expected_columns,
                    "columns_not_in_metadata": self.columns_not_in_metadata,
                    "column_sample": self.column_sample,
                    "notes": self.notes,
                }
            ]
        )


class SilverParquetQualityAgent(Agent):
    """
    Valida os Parquets da camada silver garantindo:
    - existência do arquivo
    - contagem de linhas/colunas
    - cobertura do metadata (nomes padronizados)
    """

    def __init__(self, year: int, metadata: pd.DataFrame | None):
        self.year = int(year)
        self.metadata = metadata
        self.name = f"audit-silver-{year}"
        self.allowed_sensitivity_read = ["SENSITIVE", "AGGREGATED"]
        self.allowed_sensitivity_write = ["AGGREGATED"]

    def _expected_columns(self) -> list[str]:
        if self.metadata is None or self.metadata.empty:
            return []
        subset = self.metadata[self.metadata["ano"] == self.year]
        if subset.empty:
            return []
        return (
            subset["nome_padrao"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        silver_path = paths.silver_dir() / f"microdados_enem_{self.year}.parquet"
        if not silver_path.exists():
            msg = f"[{self.name}] Arquivo SILVER não encontrado: {silver_path}"
            logger.error(msg)
            raise FileNotFoundError(silver_path)

        row_count, columns = _parquet_overview(silver_path)
        expected_columns = self._expected_columns()

        missing_expected = sorted(c for c in expected_columns if c not in columns)
        columns_not_tracked = sorted(
            c for c in columns if expected_columns and c not in expected_columns
        )

        result = ParquetQualityResult(
            layer="silver",
            year=self.year,
            parquet_path=str(silver_path),
            row_count=row_count,
            column_count=len(columns),
            column_sample=columns[:20],
            has_ano_column="ANO" in columns,
            missing_expected_columns=missing_expected or None,
            columns_not_in_metadata=columns_not_tracked or None,
            notes=None,
        )

        handle = DataHandle(
            name=f"audit_silver_{self.year}",
            sensitivity="AGGREGATED",
            payload=result.to_frame(),
        )
        ctx.add_data(handle.name, handle)
        ctx.add_log(
            f"{self.name}: {row_count} linhas, {len(columns)} colunas no Parquet SILVER."
        )
        logger.success(
            "[{}] Auditoria concluída ({} linhas / {} colunas).",
            self.name,
            row_count,
            len(columns),
        )
        return ctx


class GoldParquetAuditAgent(Agent):
    """
    Inspeciona todos os Parquets na camada gold, incluindo o metadata.
    """

    def __init__(self, metadata: pd.DataFrame | None):
        self.metadata = metadata
        self.name = "audit-gold"
        self.allowed_sensitivity_read = ["AGGREGATED"]
        self.allowed_sensitivity_write = ["AGGREGATED"]

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        gold_path = paths.gold_dir()
        parquet_files = sorted(gold_path.glob("*.parquet"))

        records: list[pd.DataFrame] = []
        for file_path in parquet_files:
            row_count, columns = _parquet_overview(file_path)
            notes = None
            if file_path.name == metadata_module.METADATA_FILE_NAME:
                notes = self._metadata_notes()

            result = ParquetQualityResult(
                layer="gold",
                year=None,
                parquet_path=str(file_path),
                row_count=row_count,
                column_count=len(columns),
                column_sample=columns[:20],
                has_ano_column="ANO" in columns,
                notes=notes,
            )
            records.append(result.to_frame())

            logger.info(
                "[{}] {} → {} linhas / {} colunas.",
                self.name,
                file_path.name,
                row_count,
                len(columns),
            )

        summary = pd.concat(records, ignore_index=True) if records else pd.DataFrame(
            columns=ParquetQualityResult(
                layer="gold",
                parquet_path="",
                row_count=0,
                column_count=0,
                column_sample=[],
            ).to_frame().columns,
        )

        handle = DataHandle(
            name="audit_gold",
            sensitivity="AGGREGATED",
            payload=summary,
        )
        ctx.add_data(handle.name, handle)
        ctx.add_log(f"{self.name}: {len(parquet_files)} arquivos GOLD auditados.")
        logger.success(
            "[{}] Auditoria GOLD concluída ({} arquivos).",
            self.name,
            len(parquet_files),
        )
        return ctx

    def _metadata_notes(self) -> str | None:
        if self.metadata is None or self.metadata.empty:
            return "Metadados indisponíveis."
        anos_meta = sorted(set(int(a) for a in self.metadata["ano"].unique()))
        expected_years = set(paths.settings.YEARS)
        missing_years = sorted(expected_years - set(anos_meta))
        if missing_years:
            return f"Metadados sem cobertura para anos: {missing_years[:5]}{'...' if len(missing_years) > 5 else ''}"
        return "Metadados cobrem todos os anos configurados."


def save_audit_report(frames: Iterable[pd.DataFrame], output_name: str) -> Path:
    """
    Salva um relatório combinado de auditoria na camada gold.
    """
    collected = [frame for frame in frames if frame is not None and not frame.empty]
    if not collected:
        combined = pd.DataFrame()
    else:
        combined = pd.concat(collected, ignore_index=True, sort=False)
    output_path = paths.gold_dir() / output_name
    write_parquet(combined, output_path)
    logger.success(
        "Relatório de auditoria salvo em {} ({} linhas).",
        output_path,
        len(combined),
    )
    return output_path
