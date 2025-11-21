from __future__ import annotations

from ..base import Agent
from ..context import OrchestratorContext, DataHandle, DatasetArtifact
from ...infra.logging import logger
from ...infra.io import write_parquet
from ...config.paths import silver_dir
from ...data.raw_to_silver import (
    RawDatasetReference,
    clean_and_standardize,
    stream_raw_to_silver,
)


class EtlRawToSilverAgent(Agent):
    def __init__(self, year: int):
        self.year = year
        self.name = f"etl-raw-to-silver-{year}"
        self.allowed_sensitivity_read = ["RAW"]
        self.allowed_sensitivity_write = ["SENSITIVE"]

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        key_in = f"raw_{self.year}"
        handle_in = ctx.get_data(key_in)
        payload = handle_in.payload

        out_path = silver_dir() / f"microdados_enem_{self.year}.parquet"

        logger.info(f"[{self.name}] Rodando ETL RAW→SILVER para {self.year}...")
        if isinstance(payload, RawDatasetReference):
            result = stream_raw_to_silver(payload)
            row_count = result.row_count
            columns = result.columns
        else:
            df_clean = clean_and_standardize(payload, self.year)
            row_count = len(df_clean)
            columns = tuple(df_clean.columns)
            write_parquet(df_clean, out_path)
            del df_clean

        handle_in.payload = None
        ctx.drop_data(key_in)
        del payload

        artifact = DatasetArtifact(
            path=out_path,
            row_count=row_count,
            columns=columns,
        )

        handle_out = DataHandle(
            name=f"silver_{self.year}",
            sensitivity="SENSITIVE",
            payload=artifact,
        )
        ctx.add_data(f"silver_{self.year}", handle_out)
        ctx.add_log(
            f"{self.name}: gerou {row_count} linhas em {out_path.name} (SILVER)."
        )
        logger.success(f"[{self.name}] ETL concluído para {self.year}.")
        return ctx
