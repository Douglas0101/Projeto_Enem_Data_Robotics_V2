from __future__ import annotations

from typing import Sequence

from ..base import Agent
from ..context import OrchestratorContext
from ...infra.logging import logger


class ValidationAgent(Agent):
    def __init__(self, year: int, required_columns: Sequence[str] | None = None):
        self.year = year
        self.name = f"validation-{year}"
        self.required_columns = list(required_columns or ["NU_INSCRICAO"])
        self.allowed_sensitivity_read = ["RAW"]
        self.allowed_sensitivity_write = ["RAW"]

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        key = f"raw_{self.year}"
        handle = ctx.get_data(key)
        df = handle.payload

        logger.info(f"[{self.name}] Validando dados RAW {self.year}...")

        if df is None or len(df) == 0:
            msg = f"[{self.name}] DataFrame RAW {self.year} está vazio."
            logger.error(msg)
            raise ValueError(msg)

        missing = [c for c in self.required_columns if c not in df.columns]
        if missing:
            msg = (
                f"[{self.name}] Colunas obrigatórias ausentes para {self.year}: {missing}"
            )
            logger.error(msg)
            raise ValueError(msg)

        logger.success(f"[{self.name}] Validação OK para {self.year}.")
        ctx.add_log(f"{self.name}: validação OK para {self.year}.")
        return ctx
