from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from enem_project.config import paths
from enem_project.config.hardware import PROFILE
from enem_project.config.settings import settings
from enem_project.infra.io import read_csv, write_parquet
from enem_project.infra.logging import logger


@dataclass
class RawDatasetReference:
    path: Path
    file_size_gb: float | None = None


@dataclass
class StreamToSilverResult:
    path: Path
    row_count: int
    columns: tuple[str, ...]


def _rename_map(year: int) -> dict[str, str]:
    """
    Mapeamento mínimo de colunas RAW → SILVER usado nos testes.
    """
    base = {
        "NU_INSCRICAO": "ID_INSCRICAO",
        "TP_SEXO": "CAT_SEXO",
        "NU_NOTA_CN": "NOTA_CIENCIAS_NATUREZA",
        "NU_NOTA_CH": "NOTA_CIENCIAS_HUMANAS",
        "NU_NOTA_LC": "NOTA_LINGUAGENS_CODIGOS",
        "NU_NOTA_MT": "NOTA_MATEMATICA",
        "NU_NOTA_REDACAO": "NOTA_REDACAO",
    }
    return base


def _raw_path(year: int) -> Path:
    return paths.raw_data_path(year)


def resolve_streaming_reference(year: int) -> RawDatasetReference | None:
    path = _raw_path(year)
    if not path.exists():
        return None
    size_gb = path.stat().st_size / (1024**3)
    if PROFILE.requires_streaming(size_gb):
        return RawDatasetReference(path=path, file_size_gb=size_gb)
    return None


def load_raw_microdados(year: int) -> pd.DataFrame:
    path = _raw_path(year)
    return read_csv(path)


def clean_and_standardize(df: pd.DataFrame, year: int) -> pd.DataFrame:
    rename_map = _rename_map(year)
    cols = [c for c in rename_map if c in df.columns]
    df_out = df[cols].rename(columns=rename_map)
    df_out["ANO"] = year
    return df_out


def stream_raw_to_silver(reference: RawDatasetReference) -> StreamToSilverResult:
    df = read_csv(reference.path)
    clean_df = clean_and_standardize(df, _infer_year_from_path(reference.path))
    silver_path = paths.silver_dir() / reference.path.name.replace(".csv", ".parquet")
    write_parquet(clean_df, silver_path)
    return StreamToSilverResult(
        path=silver_path,
        row_count=len(clean_df),
        columns=tuple(clean_df.columns),
    )


def run_raw_to_silver(year: int | Iterable[int]) -> list[StreamToSilverResult]:
    years = [year] if isinstance(year, int) else list(year)
    results: list[StreamToSilverResult] = []
    for y in years:
        ref = resolve_streaming_reference(y)
        if ref is not None:
            results.append(stream_raw_to_silver(ref))
            continue
        df_raw = load_raw_microdados(y)
        clean_df = clean_and_standardize(df_raw, y)
        silver_path = paths.silver_dir() / f"microdados_enem_{y}.parquet"
        write_parquet(clean_df, silver_path)
        results.append(
            StreamToSilverResult(
                path=silver_path,
                row_count=len(clean_df),
                columns=tuple(clean_df.columns),
            ),
        )
    return results


def _infer_year_from_path(path: Path) -> int:
    for part in path.parts:
        if part.isdigit() and len(part) == 4:
            return int(part)
    return settings.years[-1]


__all__ = [
    "RawDatasetReference",
    "StreamToSilverResult",
    "run_raw_to_silver",
    "clean_and_standardize",
    "stream_raw_to_silver",
    "load_raw_microdados",
    "resolve_streaming_reference",
]
