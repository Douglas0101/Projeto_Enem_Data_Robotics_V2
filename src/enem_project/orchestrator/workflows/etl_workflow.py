from __future__ import annotations

from datetime import datetime
import gc
from typing import Iterable

from ..base import Orchestrator
from ..context import OrchestratorContext
from ..security import SecurityManager
from ..agents.data_ingestion import DataIngestionAgent
from ..agents.validation import ValidationAgent
from ..agents.etl import EtlRawToSilverAgent
from ..agents.reporting import ReportingAgent
from ...config.settings import settings
from ...config.hardware import PROFILE
from ...infra.logging import logger


def _iter_years(target_year: int | None) -> Iterable[int]:
    if target_year is not None:
        yield target_year
    else:
        # usa a lista de anos centralizada em settings (1998–2024)
        yield from settings.years


def run_etl_for_years(years: Iterable[int]) -> dict[int, OrchestratorContext]:
    """
    Executa o workflow ETL completo para a sequência de anos informada.
    Usa o perfil de hardware local para auxiliar logging e tuning básico.
    """
    logger.info(
        "[workflow-etl] Perfil de hardware detectado: "
        f"{PROFILE.n_logical_cores} CPUs lógicos, "
        f"{PROFILE.ram_gb_total:.1f} GB RAM (disp. {PROFILE.ram_gb_available:.1f} GB), "
        f"até {PROFILE.max_ram_gb_for_pipelines:.1f} GB por pipeline, "
        f"chunks CSV ~{PROFILE.csv_chunk_rows:,} linhas, "
        f"streaming >= {PROFILE.streaming_threshold_gb:.1f} GB.",
    )

    results: dict[int, OrchestratorContext] = {}

    for y in years:
        logger.info(f"[workflow-etl] Iniciando workflow ETL para {y}...")

        security_manager = SecurityManager(policies={})

        agents = [
            DataIngestionAgent(y),
            ValidationAgent(y),
            EtlRawToSilverAgent(y),
            ReportingAgent(y),
        ]

        orchestrator = Orchestrator(agents=agents, security_manager=security_manager)

        ctx = OrchestratorContext(
            run_id=f"etl-{y}-{datetime.utcnow().isoformat(timespec='seconds')}",
            params={"year": y},
        )

        ctx = orchestrator.run(ctx)
        results[y] = ctx

        logger.success(f"[workflow-etl] Workflow ETL concluído para {y}.")

        # Libera memória agressivamente entre anos para evitar pressão de RAM
        # em execuções longas (1998–2024) em máquinas locais.
        gc.collect()

    return results


def run_etl_full(year: int | None = None) -> dict[int, OrchestratorContext]:
    """
    Roda o workflow ETL completo (RAW → SILVER + QA) para um ano
    específico ou para todos os anos configurados em settings.years.
    """
    return run_etl_for_years(_iter_years(year))
