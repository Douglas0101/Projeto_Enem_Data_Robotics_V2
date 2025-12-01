from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from enem_project.config.paths import gold_dir
from enem_project.infra.logging import logger

METADATA_FILE_NAME = "variaveis_meta.parquet"


def _metadata_path() -> Path:
    path = gold_dir() / METADATA_FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _collect_small_domain(series: pd.Series, max_size: int = 20) -> list | None:
    """
    Coleta valores únicos preservando a ordem de aparição até um limite.

    Se o limite for ultrapassado, retorna None imediatamente para evitar
    alocação excessiva de memória.
    """
    seen: list = []
    seen_set = set()
    for value in series:
        if pd.isna(value):
            continue
        if value not in seen_set:
            seen.append(value)
            seen_set.add(value)
            if len(seen) > max_size:
                return None
    return seen


@dataclass
class MetadataRecord:
    ano: int
    nome_original: str
    nome_padrao: str
    descricao: str | None = None
    tipo_padrao: str | None = None
    dominio_valores: list | None = None


def save_metadata(df: pd.DataFrame) -> Path:
    path = _metadata_path()
    logger.info("Salvando metadados em {}", path)
    df.to_parquet(path, index=False)
    return path


def load_metadata() -> pd.DataFrame:
    path = _metadata_path()
    if not path.exists():
        raise FileNotFoundError(path)
    logger.info("Carregando metadados de {}", path)
    return pd.read_parquet(path)


def filter_metadata_for_year(metadata: pd.DataFrame, year: int) -> pd.DataFrame:
    if "ano" not in metadata.columns:
        return metadata.copy()
    return metadata[metadata["ano"] == year].reset_index(drop=True)


__all__ = [
    "METADATA_FILE_NAME",
    "MetadataRecord",
    "_collect_small_domain",
    "save_metadata",
    "load_metadata",
    "filter_metadata_for_year",
]
