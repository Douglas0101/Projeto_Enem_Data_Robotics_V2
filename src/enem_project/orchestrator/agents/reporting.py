from __future__ import annotations

import pandas as pd

from ..base import Agent
from ..context import OrchestratorContext, DataHandle, DatasetArtifact
from ...infra.logging import logger


class ReportingAgent(Agent):
    def __init__(self, year: int):
        self.year = year
        self.name = f"reporting-{year}"
        self.allowed_sensitivity_read = ["SENSITIVE"]
        self.allowed_sensitivity_write = ["AGGREGATED"]

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        key_silver = f"silver_{self.year}"
        handle_silver = ctx.get_data(key_silver)
        payload = handle_silver.payload

        row_count: int
        if isinstance(payload, DatasetArtifact):
            row_count = payload.row_count
        elif isinstance(payload, pd.DataFrame):
            row_count = len(payload)
        else:
            raise TypeError(
                f"[{self.name}] Payload inesperado para {key_silver}: {type(payload)}"
            )

        logger.info(f"[{self.name}] Gerando resumo AGGREGATED para {self.year}...")

        summary = pd.DataFrame(
            {
                "ANO": [self.year],
                "n_linhas_silver": [row_count],
            }
        )

        handle_out = DataHandle(
            name=f"qa_summary_{self.year}",
            sensitivity="AGGREGATED",
            payload=summary,
        )
        ctx.add_data(f"qa_summary_{self.year}", handle_out)
        ctx.add_log(
            f"{self.name}: resumo QA para {self.year} (n_linhas_silver={row_count})."
        )

        handle_silver.payload = None
        ctx.drop_data(key_silver)

        logger.success(f"[{self.name}] Resumo QA gerado para {self.year}.")
        return ctx
