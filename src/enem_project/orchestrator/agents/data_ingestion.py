from __future__ import annotations

from ..base import Agent
from ..context import OrchestratorContext, DataHandle
from ...infra.logging import logger
from ...data.raw_to_silver import load_raw_microdados, resolve_streaming_reference


class DataIngestionAgent(Agent):
    def __init__(self, year: int):
        self.year = year
        self.name = f"data-ingestion-{year}"
        self.allowed_sensitivity_read = []
        self.allowed_sensitivity_write = ["RAW"]

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        logger.info(f"[{self.name}] Iniciando ingestão de dados RAW para {self.year}...")
        ref = resolve_streaming_reference(self.year)

        if ref is not None:
            logger.info(
                "[{}] Detected streaming mode (arquivo ~{:.2f} GB). Nenhum DataFrame será carregado agora.",
                self.name,
                (ref.file_size_gb or 0.0),
            )
            handle = DataHandle(
                name=f"raw_{self.year}",
                sensitivity="RAW",
                payload=ref,
            )
            ctx.add_data(f"raw_{self.year}", handle)
            ctx.add_log(
                f"{self.name}: streaming habilitado para ano {self.year} "
                f"(arquivo ~{(ref.file_size_gb or 0.0):.2f} GB).",
            )
            logger.success(f"[{self.name}] Referência RAW registrada para streaming.")
            return ctx

        df_raw = load_raw_microdados(self.year)

        handle = DataHandle(
            name=f"raw_{self.year}",
            sensitivity="RAW",
            payload=df_raw,
        )
        ctx.add_data(f"raw_{self.year}", handle)
        ctx.add_log(f"{self.name}: carregou {len(df_raw)} linhas de RAW {self.year}.")

        logger.success(f"[{self.name}] Concluído: {len(df_raw)} linhas.")
        return ctx
