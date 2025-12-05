from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from typing import Optional

import pandas as pd

from enem_project.config import paths
from enem_project.config.hardware import PROFILE
from enem_project.config.settings import settings
from enem_project.infra.io import (
    read_csv,
    write_parquet,
    iter_csv_chunks,
    append_to_parquet,
)
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


@dataclass(frozen=True)
class ColumnSpec:
    target: str
    aliases: tuple[str, ...]
    kind: str  # "string", "upper", "integer", "numeric"


NOTE_COLUMNS: tuple[str, ...] = (
    "NOTA_CIENCIAS_NATUREZA",
    "NOTA_CIENCIAS_HUMANAS",
    "NOTA_LINGUAGENS_CODIGOS",
    "NOTA_MATEMATICA",
    "NOTA_REDACAO",
)

BASE_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec(
        "ID_INSCRICAO",
        ("NU_SEQUENCIAL", "ID_INSCRICAO", "NU_INSCRICAO", "INSCRICAO"),
        "string",
    ),
    ColumnSpec("ANO", ("ANO", "NU_ANO"), "integer"),
    ColumnSpec("SG_UF_PROVA", ("SG_UF_PROVA", "SG_UF_RESIDENCIA", "UF_PROVA"), "upper"),
    ColumnSpec(
        "CO_MUNICIPIO_PROVA",
        ("CO_MUNICIPIO_PROVA", "CO_MUNICIPIO_RESIDENCIA", "COD_MUNICIPIO_PROVA"),
        "string",
    ),
    ColumnSpec(
        "NO_MUNICIPIO_PROVA",
        ("NO_MUNICIPIO_PROVA", "NO_MUNICIPIO_RESIDENCIA", "MUNICIPIO_PROVA"),
        "string",
    ),
    ColumnSpec("TP_SEXO", ("TP_SEXO", "SEXO", "CAT_SEXO"), "upper"),
    ColumnSpec("TP_COR_RACA", ("TP_COR_RACA", "TP_ETNIA"), "integer"),
    ColumnSpec("TP_FAIXA_ETARIA", ("TP_FAIXA_ETARIA",), "integer"),
    ColumnSpec("NU_IDADE", ("NU_IDADE", "IDADE"), "integer"),
    ColumnSpec("Q006", ("Q006", "Q06"), "string"),
    ColumnSpec("TP_PRESENCA_CN", ("TP_PRESENCA_CN",), "integer"),
    ColumnSpec("TP_PRESENCA_CH", ("TP_PRESENCA_CH",), "integer"),
    ColumnSpec("TP_PRESENCA_LC", ("TP_PRESENCA_LC",), "integer"),
    ColumnSpec("TP_PRESENCA_MT", ("TP_PRESENCA_MT",), "integer"),
    ColumnSpec("TP_STATUS_REDACAO", ("TP_STATUS_REDACAO",), "integer"),
    ColumnSpec(
        "NOTA_CIENCIAS_NATUREZA",
        ("NOTA_CIENCIAS_NATUREZA", "NU_NOTA_CN", "NOTA_CN", "NT_CN"),
        "numeric",
    ),
    ColumnSpec(
        "NOTA_CIENCIAS_HUMANAS",
        ("NOTA_CIENCIAS_HUMANAS", "NU_NOTA_CH", "NOTA_CH", "NT_CH"),
        "numeric",
    ),
    ColumnSpec(
        "NOTA_LINGUAGENS_CODIGOS",
        ("NOTA_LINGUAGENS_CODIGOS", "NU_NOTA_LC", "NOTA_LC", "NT_LC"),
        "numeric",
    ),
    ColumnSpec(
        "NOTA_MATEMATICA",
        ("NOTA_MATEMATICA", "NU_NOTA_MT", "NOTA_MT", "NT_MT"),
        "numeric",
    ),
    ColumnSpec(
        "NOTA_REDACAO",
        ("NOTA_REDACAO", "NU_NOTA_REDACAO", "NU_NOTA_COMP5", "NT_REDACAO"),
        "numeric",
    ),
)


def _rename_map(year: int) -> dict[str, str]:
    """
    Mapeamento bruto → canônico derivado do schema consolidado.

    Mantido por compatibilidade com testes/usuários que ainda dependam
    do dicionário de renomeação simples.
    """
    mapping: dict[str, str] = {}
    for spec in BASE_COLUMNS:
        for alias in spec.aliases:
            mapping[alias] = spec.target
    return mapping


def _raw_path(year: int) -> Path:
    return paths.raw_data_path(year)


def _results_path(year: int) -> Path:
    base = paths.raw_dir() / f"microdados_enem_{year}" / "DADOS"
    return base / f"RESULTADOS_{year}.csv"


def _select_source_column(df: pd.DataFrame, aliases: tuple[str, ...]) -> Optional[str]:
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


def _coerce_string(series: pd.Series, upper: bool = False) -> pd.Series:
    coerced = pd.Series(series, copy=False).astype("string").str.strip()
    if upper:
        coerced = coerced.str.upper()
    return coerced


def _coerce_numeric(series: pd.Series, integer: bool = False) -> pd.Series:
    """
    Converte para número, tratando vírgula decimal PT-BR e valores fora
    do formato esperado. Inteiros são retornados como Int64 para suportar NaN.
    """
    as_str = pd.Series(series, copy=False).astype("string")
    cleaned = as_str.str.replace(",", ".", regex=False)
    numeric = pd.to_numeric(cleaned, errors="coerce")
    if integer:
        return numeric.round().astype("Int64")
    return numeric.astype(float)


def _apply_score_sanitization(df: pd.DataFrame) -> pd.DataFrame:
    for col in NOTE_COLUMNS:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        valid = series.between(0, 1000)
        df[col] = series.where(valid)
    return df


def _apply_age_sanitization(df: pd.DataFrame) -> pd.DataFrame:
    if "NU_IDADE" not in df.columns:
        return df
    series = pd.to_numeric(df["NU_IDADE"], errors="coerce")
    valid = series.between(8, 120)
    df["NU_IDADE"] = series.where(valid)
    return df


def resolve_streaming_reference(year: int) -> RawDatasetReference | None:
    path = _raw_path(year)
    if not path.exists():
        return None
    size_gb = path.stat().st_size / (1024**3)
    if PROFILE.requires_streaming(size_gb):
        return RawDatasetReference(path=path, file_size_gb=size_gb)
    return None


def load_raw_microdados(year: int) -> pd.DataFrame:
    """
    Carrega o CSV bruto preferencial para o ano.

    Para anos recentes (ex.: 2024) o INEP separou os microdados em
    PARTICIPANTES_YYYY.csv (socioeconômico) e RESULTADOS_YYYY.csv
    (notas). Se o arquivo principal MICRODADOS não tiver colunas de
    nota, caímos para RESULTADOS para preservar as notas.
    """
    path = _raw_path(year)
    results_path = _results_path(year)

    def _has_score_columns(p: Path) -> bool:
        if not p.exists():
            return False
        try:
            read_csv(
                p,
                usecols=[
                    "NU_NOTA_CN",
                    "NU_NOTA_CH",
                    "NU_NOTA_LC",
                    "NU_NOTA_MT",
                    "NU_NOTA_REDACAO",
                ],
                chunk_rows=10,
            )
            return True
        except Exception:
            return False

    if _has_score_columns(path):
        return read_csv(path)

    if _has_score_columns(results_path):
        logger.warning(
            "Arquivo MICRODADOS {} não contém colunas de nota; usando RESULTADOS_{}.csv para preservar notas.",
            path.name,
            year,
        )
        return read_csv(results_path)

    logger.error(
        "Nenhum CSV com notas encontrado para o ano {} (checado {} e {}).",
        year,
        path,
        results_path,
    )
    return read_csv(path)


def _empty_series(length: int, kind: str) -> pd.Series:
    if kind in {"numeric"}:
        return pd.Series([pd.NA] * length, dtype="Float64")
    if kind == "integer":
        return pd.Series([pd.NA] * length, dtype="Int64")
    return pd.Series([pd.NA] * length, dtype="string")


def _coerce_column(df: pd.DataFrame, spec: ColumnSpec) -> pd.Series:
    source = _select_source_column(df, spec.aliases)
    if source is None:
        return _empty_series(len(df), spec.kind)

    if spec.kind == "string":
        return _coerce_string(df[source], upper=False)
    if spec.kind == "upper":
        return _coerce_string(df[source], upper=True)
    if spec.kind == "integer":
        return _coerce_numeric(df[source], integer=True)
    if spec.kind == "numeric":
        return _coerce_numeric(df[source], integer=False)
    raise ValueError(f"Tipo de coluna desconhecido: {spec.kind}")


def clean_and_standardize(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Normaliza o RAW em um schema canônico resiliente a variações de nome
    e tipo, inspirado no pipeline robusto do notebook Colab.
    """
    coerced_columns = {}
    for spec in BASE_COLUMNS:
        coerced = _coerce_column(df, spec)
        coerced.name = spec.target
        coerced_columns[spec.target] = coerced

    df_out = pd.DataFrame(coerced_columns)

    # Normaliza ANO e ID_INSCRICAO (sempre presentes no schema final).
    df_out["ANO"] = (
        pd.to_numeric(df_out["ANO"], errors="coerce").fillna(year).astype(int)
    )
    df_out["ID_INSCRICAO"] = _coerce_string(df_out["ID_INSCRICAO"], upper=False)

    df_out = _apply_score_sanitization(df_out)
    df_out = _apply_age_sanitization(df_out)
    desired_order = [spec.target for spec in BASE_COLUMNS]
    return df_out[desired_order]


def stream_raw_to_silver(reference: RawDatasetReference) -> StreamToSilverResult:
    year = _infer_year_from_path(reference.path)
    silver_path = paths.silver_dir() / reference.path.name.replace(".csv", ".parquet")

    # Garante que começamos um arquivo novo
    if silver_path.exists():
        silver_path.unlink()

    total_rows = 0
    last_columns = tuple()

    logger.info(
        f"Iniciando processamento streaming de {reference.path} para {silver_path}..."
    )

    # Itera sobre chunks do CSV para não estourar a memória
    for chunk_df in iter_csv_chunks(reference.path, chunk_rows=PROFILE.csv_chunk_rows):
        clean_chunk = clean_and_standardize(chunk_df, year)

        if not clean_chunk.empty:
            append_to_parquet(clean_chunk, silver_path)
            total_rows += len(clean_chunk)
            last_columns = tuple(clean_chunk.columns)

            logger.debug(
                f"Processado chunk com {len(clean_chunk)} linhas. Total acumulado: {total_rows}"
            )

    logger.success(
        f"Streaming concluído. Arquivo salvo em {silver_path} com {total_rows} linhas."
    )

    return StreamToSilverResult(
        path=silver_path,
        row_count=total_rows,
        columns=last_columns,
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
