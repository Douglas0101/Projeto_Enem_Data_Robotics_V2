from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from duckdb import DuckDBPyConnection

from ..infra.db import default_db_path, get_duckdb_conn


@contextmanager
def duckdb_readonly_conn() -> Iterator[DuckDBPyConnection]:
    """
    Fornece uma conexão DuckDB em modo somente leitura, adequada para
    uso pela API (dashboard, Horizon UI, etc.).

    Pré-condição: o arquivo enem.duckdb e as tabelas/views de interesse
    devem ter sido inicializados previamente via:
        enem --sql-backend
    """
    conn = get_duckdb_conn(default_db_path(), read_only=True)
    try:
        yield conn
    finally:
        conn.close()

