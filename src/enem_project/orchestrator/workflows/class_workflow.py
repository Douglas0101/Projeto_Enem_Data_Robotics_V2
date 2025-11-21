from __future__ import annotations

from datetime import UTC, datetime
import gc
from typing import Iterable

from ..base import Orchestrator
from ..context import OrchestratorContext
from ..security import SecurityManager
from ..agents.cleaning import CleanseAgent
from ..agents.class_engineering import ClassEngineeringAgent
from ...config.settings import settings
from ...config.hardware import PROFILE
from ...infra.logging import logger


def _iter_years(target_year: int | None) -> Iterable[int]:
    if target_year is not None:
        yield target_year
    else:
        yield from settings.years


def run_class_workflow(years: Iterable[int]) -> dict[int, OrchestratorContext]:
    """
    Executa o fluxo de limpeza + engenharia de classes para os anos informados.
    """
    results: dict[int, OrchestratorContext] = {}

    logger.info(
        "[class-workflow] Perfil de hardware detectado: "
        f"{PROFILE.n_logical_cores} CPUs lógicos, "
        f"{PROFILE.ram_gb_total:.1f} GB RAM (disp. {PROFILE.ram_gb_available:.1f} GB), "
        f"até {PROFILE.max_ram_gb_for_pipelines:.1f} GB por pipeline, "
        f"chunks CSV ~{PROFILE.csv_chunk_rows:,} linhas, "
        f"streaming >= {PROFILE.streaming_threshold_gb:.1f} GB.",
    )

    for year in years:
        logger.info("[class-workflow] Iniciando pipeline de classes para %s", year)
        security_manager = SecurityManager(policies={})
        agents = [
            CleanseAgent(year),
            ClassEngineeringAgent(year),
        ]
        orchestrator = Orchestrator(agents=agents, security_manager=security_manager)
        ctx = OrchestratorContext(
            run_id=f"class-{year}-{datetime.now(UTC).isoformat(timespec='seconds')}",
            params={"year": year},
        )
        ctx = orchestrator.run(ctx)
        results[year] = ctx
        logger.success("[class-workflow] Pipeline concluído para %s", year)

        # Libera memória agressivamente entre anos, espelhando o workflow ETL.
        gc.collect()

    return results


def run_class_workflow_all(year: int | None = None) -> dict[int, OrchestratorContext]:
    return run_class_workflow(_iter_years(year))
