from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

import pandas as pd

from ..base import Orchestrator
from ..context import OrchestratorContext
from ..security import SecurityManager
from ..agents.parquet_quality import (
    GoldParquetAuditAgent,
    SilverParquetQualityAgent,
    save_audit_report,
)
from ...config.settings import settings
from ...data.metadata import load_metadata
from ...infra.logging import logger


def run_quality_audit_for_years(
    years: Iterable[int],
    *,
    output_name: str = "parquet_audit_report.parquet",
) -> dict[str, pd.DataFrame]:
    """
    Executa a auditoria de Parquets para os anos informados, seguindo o
    modelo de orquestração por agentes. Retorna os DataFrames consolidados
    (silver, gold e combinado) e escreve o relatório completo na camada gold.
    """
    metadata = load_metadata()
    silver_frames: list[pd.DataFrame] = []
    results: dict[int, OrchestratorContext] = {}

    year_list = list(years)

    logger.info(
        "[audit-workflow] Iniciando auditoria de Parquets para anos: {}",
        year_list,
    )
    for year in year_list:
        security_manager = SecurityManager(policies={})
        agents = [SilverParquetQualityAgent(year, metadata)]
        orchestrator = Orchestrator(agents=agents, security_manager=security_manager)
        run_id = f"audit-silver-{year}-{datetime.now(UTC).isoformat(timespec='seconds')}"
        ctx = OrchestratorContext(run_id=run_id, params={"year": year})
        ctx = orchestrator.run(ctx)
        results[year] = ctx
        handle = ctx.get_data(f"audit_silver_{year}")
        silver_frames.append(handle.payload)

    silver_df = (
        pd.concat(silver_frames, ignore_index=True)
        if silver_frames
        else pd.DataFrame()
    )

    gold_security = SecurityManager(policies={})
    gold_agents = [GoldParquetAuditAgent(metadata)]
    gold_orchestrator = Orchestrator(gold_agents, gold_security)
    gold_run_id = f"audit-gold-{datetime.now(UTC).isoformat(timespec='seconds')}"
    gold_ctx = OrchestratorContext(run_id=gold_run_id, params={"scope": "gold"})
    gold_ctx = gold_orchestrator.run(gold_ctx)
    gold_df = gold_ctx.get_data("audit_gold").payload

    combined_frames = [silver_df, gold_df]
    report_path = save_audit_report(combined_frames, output_name)
    logger.success(
        "[audit-workflow] Auditoria concluída. Relatório consolidado em {}.",
        report_path,
    )
    return {"silver": silver_df, "gold": gold_df, "report_path": report_path}
