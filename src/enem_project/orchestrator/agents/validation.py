from __future__ import annotations

from typing import Sequence

from ..base import Agent
from ..context import OrchestratorContext
from ...infra.logging import logger
from ...data.raw_to_silver import BASE_COLUMNS


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

        missing = []
        for req_col in self.required_columns:
            # Tenta encontrar a especificação da coluna em BASE_COLUMNS
            spec = next(
                (s for s in BASE_COLUMNS if req_col == s.target or req_col in s.aliases),
                None
            )

            if spec:
                # Se encontrou spec, verifica se ALGUM alias está presente no DF
                found_alias = any(alias in df.columns for alias in spec.aliases)
                if not found_alias:
                    missing.append(req_col)
            else:
                # Se não encontrou spec, verifica match exato (comportamento legado)
                if req_col not in df.columns:
                    missing.append(req_col)

        if missing:
            msg = (
                f"[{self.name}] Colunas obrigatórias ausentes para {self.year}: {missing} "
                f"(verifique aliases em BASE_COLUMNS se aplicável)"
            )
            logger.error(msg)
            raise ValueError(msg)

        logger.success(f"[{self.name}] Validação OK para {self.year}.")
        ctx.add_log(f"{self.name}: validação OK para {self.year}.")
        return ctx
