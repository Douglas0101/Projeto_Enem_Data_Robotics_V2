from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from ..config.hardware import PROFILE
from .logging import logger

try:  # pragma: no cover - duckdb é opcional em ambientes de teste
    import duckdb
except ImportError:  # pragma: no cover
    duckdb = None


def _should_use_duckdb(encoding: str) -> bool:
    """
    DuckDB só suporta leitura de CSV em UTF-8 nesse fluxo. Se o arquivo
    estiver em outro encoding (ex.: Latin-1), pulamos direto para o fallback.
    """
    if duckdb is None:
        return False
    return encoding.lower() in {"utf-8", "utf8"}


def _read_csv_with_duckdb(
    path: Path,
    separator: str,
) -> pd.DataFrame:
    relation = duckdb.read_csv(  # type: ignore[union-attr]
        str(path),
        sep=separator,
        header=True,
        all_varchar=True,
        ignore_errors=True,
        parallel=False,
    )
    return relation.to_df()


def _concat_chunks(chunks: list[pd.DataFrame]) -> pd.DataFrame:
    if not chunks:
        return pd.DataFrame()
    if len(chunks) == 1:
        return chunks[0].reset_index(drop=True)
    try:
        return pd.concat(chunks, ignore_index=True, copy=False)
    except TypeError:  # pandas < 2.1 não aceita copy=
        return pd.concat(chunks, ignore_index=True)


def _read_csv_with_pandas(
    path: Path,
    separator: str,
    encoding: str,
    *,
    low_memory: bool,
    usecols: Sequence[str] | None,
    dtype: Mapping[str, Any] | None,
    chunk_rows: int | None,
) -> pd.DataFrame:
    kwargs: dict[str, Any] = {
        "sep": separator,
        "encoding": encoding,
        "low_memory": low_memory,
        "usecols": usecols,
        "dtype": dtype,
        "on_bad_lines": "warn",
    }

    if chunk_rows is None or chunk_rows <= 0:
        return _pandas_read_csv(path, kwargs)

    kwargs["chunksize"] = chunk_rows
    reader = _pandas_read_csv(path, kwargs)
    chunks: list[pd.DataFrame] = []
    try:
        for chunk in reader:  # type: ignore[attr-defined]
            chunks.append(chunk)
    finally:
        close = getattr(reader, "close", None)
        if callable(close):
            close()
    return _concat_chunks(chunks)


def _pandas_read_csv(path: Path, kwargs: dict[str, Any]):
    panda_kwargs = dict(kwargs)
    panda_kwargs.setdefault("encoding_errors", "replace")
    try:
        return pd.read_csv(
            path,
            dtype_backend="pyarrow",
            **panda_kwargs,
        )
    except TypeError:  # pandas sem suporte a dtype_backend
        panda_kwargs.pop("dtype_backend", None)
        return pd.read_csv(path, **panda_kwargs)


def read_csv(
    path: Path,
    separator: str = ";",
    encoding: str = "latin-1",
    *,
    usecols: Sequence[str] | None = None,
    dtype: Mapping[str, Any] | None = None,
    low_memory: bool = False,
    chunk_rows: int | None = None,
) -> pd.DataFrame:
    """
    Lê um CSV com fallback automático para pandas + chunks quando DuckDB
    não puder ser utilizado (por exemplo, arquivos Latin-1).
    """
    chunk_size = chunk_rows if chunk_rows is not None else PROFILE.csv_chunk_rows
    logger.info(f"Lendo CSV de: {path}")

    if _should_use_duckdb(encoding):
        try:
            df = _read_csv_with_duckdb(path, separator)
            logger.success(f"Leitura concluída via DuckDB: {len(df)} linhas em {path.name}")
            return df
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "DuckDB falhou ao ler {} ({}). Caindo para pandas com chunks de {} linhas.",
                path,
                exc,
                chunk_size,
            )
    else:
        reason = "DuckDB indisponível" if duckdb is None else f"encoding '{encoding}' não suportado pelo DuckDB"
        logger.debug(
            "Pulando leitura via DuckDB para {} ({}). Usando pandas com chunks de {} linhas.",
            path,
            reason,
            chunk_size,
        )

    df = _read_csv_with_pandas(
        path,
        separator,
        encoding,
        low_memory=low_memory,
        usecols=usecols,
        dtype=dtype,
        chunk_rows=chunk_size,
    )
    logger.success(f"Leitura concluída via pandas: {len(df)} linhas em {path.name}")
    return df


def iter_csv_chunks(
    path: Path,
    separator: str = ";",
    encoding: str = "latin-1",
    *,
    usecols: Sequence[str] | None = None,
    dtype: Mapping[str, Any] | None = None,
    low_memory: bool = False,
    chunk_rows: int | None = None,
) -> Iterator[pd.DataFrame]:
    """
    Iterador sobre um CSV em chunks fixos utilizando pandas. Útil para
    pipelines streaming que não podem carregar o arquivo inteiro na RAM.
    """
    chunk_size = chunk_rows if chunk_rows is not None else PROFILE.csv_chunk_rows
    if chunk_size <= 0:
        raise ValueError("chunk_rows deve ser positivo para leitura streaming.")

    kwargs: dict[str, Any] = {
        "sep": separator,
        "encoding": encoding,
        "low_memory": low_memory,
        "usecols": usecols,
        "dtype": dtype,
        "on_bad_lines": "warn",
        "chunksize": chunk_size,
    }

    reader = _pandas_read_csv(path, kwargs)
    try:
        for chunk in reader:  # type: ignore[attr-defined]
            yield chunk
    finally:
        close = getattr(reader, "close", None)
        if callable(close):
            close()


def read_parquet(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """
    Lê um arquivo Parquet com logging padronizado.
    """
    logger.info(f"Lendo Parquet de: {path}")
    try:
        df = pd.read_parquet(path, columns=columns)
        logger.success(f"Leitura concluída: {len(df)} linhas em {path.name}")
        return df
    except FileNotFoundError:
        logger.error(f"Arquivo Parquet não encontrado: {path}")
        raise
    except Exception as e:  # noqa: BLE001
        logger.error(f"Erro inesperado ao ler Parquet {path}: {e}")
        raise


def write_parquet(
    df: pd.DataFrame,
    path: Path,
    *,
    compression: str = "snappy",
) -> None:
    """
    Salva um DataFrame em Parquet com logging padronizado.
    """
    logger.info(f"Gravando arquivo Parquet em: {path}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False, compression=compression)
        logger.success(f"Arquivo {path.name} salvo com {len(df)} linhas.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Falha ao escrever Parquet em {path}: {e}")
        raise


def append_to_parquet(
    df: pd.DataFrame,
    path: Path,
    *,
    compression: str = "snappy",
) -> None:
    """
    Adiciona um DataFrame a um arquivo Parquet existente, ou cria um novo
    se não existir. Utiliza pyarrow para escrita eficiente.
    """
    if not path.exists():
        write_parquet(df, path, compression=compression)
        return

    import pyarrow as pa
    import pyarrow.parquet as pq

    try:
        table = pa.Table.from_pandas(df, preserve_index=False)
        with pq.ParquetWriter(
            path,
            table.schema,
            compression=compression,
            filesystem=None,  # Local filesystem
        ) as writer:
            writer.write_table(table)
    except Exception as e:
        logger.error(f"Falha ao fazer append no Parquet {path}: {e}")
        # Fallback: leitura total + concat + reescrita (lento e memória-intensivo, mas seguro)
        # Em um cenário ideal de streaming, o arquivo deve ser aberto em modo append ou
        # escrito como múltiplos arquivos em um diretório (dataset particionado).
        # Como parquet não suporta append nativo em arquivo único fechado facilmente,
        # a melhor prática para "append" é escrever partição separada ou dataset.
        # Mas para manter compatibilidade com arquivo único:
        try:
            existing = pd.read_parquet(path)
            combined = pd.concat([existing, df], ignore_index=True)
            write_parquet(combined, path, compression=compression)
        except Exception as e2:
            logger.error(f"Falha crítica no fallback de append: {e2}")
            raise e
