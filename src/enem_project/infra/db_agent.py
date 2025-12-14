"""
Módulo responsável pelo gerenciamento de conexões e execução de queries
no DuckDB, fornecendo uma camada de abstração com guardrails de segurança e
suporte a concorrência segura em ambientes multi-thread.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Optional

import duckdb

from enem_project.config.paths import gold_dir, silver_dir
from enem_project.infra.logging import logger

# Use RLock (Reentrant Lock) to prevent deadlocks if the same thread
# needs to acquire it recursively.
_DB_LOCK = threading.RLock()
_GLOBAL_CONN: Optional[duckdb.DuckDBPyConnection] = None
_GLOBAL_DB_PATH: Optional[Path] = None


class DuckDBLockError(RuntimeError):
    """
    Erro lançado quando o arquivo DuckDB está bloqueado por outro processo.
    """


def default_db_path() -> Path:
    """
    Caminho padrão do banco DuckDB usado para consultas SQL sobre
    as camadas silver/gold.
    """
    return gold_dir().parent / "enem.duckdb"


class DuckDBAgent:
    """
    Agente de dados responsável por gerenciar conexões e execuções
    de queries no DuckDB com guardrails de segurança e auditoria básica.
    """

    def __init__(self, db_path: Optional[Path | str] = None, read_only: bool = True):
        self.db_path = Path(db_path) if db_path else default_db_path()
        self.read_only = read_only
        if not self.read_only:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        """
        Obtém a conexão DuckDB.
        ATENÇÃO: Em modo read-only, sempre retorna uma NOVA conexão para
        garantir isolamento entre threads do Uvicorn/FastAPI e evitar segfaults
        (shared_ptr is NULL). O custo de conectar em RO é baixo.
        (shared_ptr is NULL). O custo de conectar em RO é baixo.
        """
        if self.read_only:
            # Desabilita Singleton Global para evitar race conditions em
            # threads
            # O DuckDB suporta múltiplas conexões de leitura simultâneas ao
            # mesmo arquivo.
            max_mem = os.getenv("DUCKDB_MAX_MEMORY", "4GB")
            logger.debug(
                f"Connecting to DuckDB (read_only=True, dedicated thread, "
                f"max_memory={max_mem}): {self.db_path}"
            )

            try:
                return duckdb.connect(
                    self.db_path.as_posix(),
                    read_only=True,
                    config={"access_mode": "READ_ONLY", "max_memory": max_mem},
                )
            except Exception as e:
                logger.error(f"Failed to connect to DuckDB: {e}")
                raise

        # Non-read-only logic (dedicated connection for writes)
        if self._conn is not None:
            return self._conn

        logger.info(
            f"Connecting to DuckDB: {self.db_path} (read_only={self.read_only})"
        )
        try:
            self._conn = duckdb.connect(
                self.db_path.as_posix(), read_only=self.read_only
            )
        except duckdb.IOException as e:
            if "lock" in str(e).lower():
                raise DuckDBLockError(
                    "Não foi possível adquirir o lock de escrita no banco de "
                    f"dados ({self.db_path}).\n"
                    "Provavelmente o servidor da API (Dashboard) ou outro "
                    "processo CLI está rodando.\n"
                    "Por favor, encerre o servidor/dashboard antes de "
                    "executar operações de escrita (ETL/SQL Backend).\n"
                    f"Detalhes: {e}"
                ) from e
            raise e
        return self._conn

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Retorna uma conexão DuckDB usando a estratégia definida."""
        return self._get_conn()

    def close(self):
        """Fecha a conexão com o DuckDB se estiver aberta."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _enforce_guardrails(self, sql: str, row_limit: int = 10000) -> str:
        """
        Aplica guardrails básicos.
        """
        sql_lower = sql.lower().strip()

        if self.read_only:
            forbidden = [
                "drop ",
                "delete ",
                "truncate ",
                "update ",
                "insert ",
                "alter ",
            ]
            if any(cmd in sql_lower for cmd in forbidden):
                raise ValueError(
                    "Comando potencialmente destrutivo bloqueado em modo "
                    f"read-only: {sql[:50]}..."
                )

        if sql_lower.startswith("select") and "limit" not in sql_lower:
            logger.warning(
                f"Query sem LIMIT detectada. Aplicando LIMIT {row_limit} "
                "automaticamente."
            )
            if sql.strip().endswith(";"):
                sql = sql.strip()[:-1] + f" LIMIT {row_limit};"
            else:
                sql = sql + f" LIMIT {row_limit}"

        return sql

    def run_query(
        self, sql: str, params: Optional[list[Any]] = None, row_limit: int = 50000
    ) -> tuple[list[Any], list[str]]:
        """
        Executa uma query SQL de forma thread-safe e retorna resultados
        e colunas.
        """
        guarded_sql = self._enforce_guardrails(sql, row_limit=row_limit)

        if self.read_only:
            # CRITICAL: Acquire lock BEFORE getting connection or executing
            # anything. This prevents race conditions during connection init
            # or liveness checks.
            with _DB_LOCK:
                conn = self._get_conn()
                try:
                    # Execute and fetch inside the lock
                    cursor = (
                        conn.execute(guarded_sql, params)
                        if params
                        else conn.execute(guarded_sql)
                    )
                    rows = cursor.fetchall()
                    description = cursor.description

                    columns = [d[0] for d in description] if description else []
                    return rows, columns
                except Exception as e:
                    logger.error(f"Erro na execução da query: {e}")
                    # If connection seems broken, maybe we should invalidate
                    # _GLOBAL_CONN here? For now, just raise.
                    raise
        else:
            # Read-write mode (usually single thread or dedicated agent)
            conn = self._get_conn()
            try:
                logger.debug(f"Executando query (RW): {guarded_sql[:200]}...")
                cursor = (
                    conn.execute(guarded_sql, params)
                    if params
                    else conn.execute(guarded_sql)
                )
                rows = cursor.fetchall()
                description = cursor.description
                columns = [d[0] for d in description] if description else []
                return rows, columns
            except Exception as e:
                logger.error(f"Erro na execução da query: {e}")
                raise

    def execute_script(self, sql_script: str):
        """Executa um script SQL completo (vários comandos)."""
        if self.read_only:
            raise ValueError("Não é possível executar scripts DDL em modo read-only.")

        conn = self._get_conn()
        try:
            conn.execute(sql_script)
            logger.info("Script SQL executado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao executar script: {e}")
            raise

    def register_parquet_views(self):
        """Registra as views do Lakehouse no DuckDB."""
        if self.read_only:
            logger.warning("Tentativa de registrar views em modo read-only ignorada.")
            return

        s_dir = silver_dir()
        g_dir = gold_dir()
        conn = self._get_conn()

        views = {
            "silver_microdados": s_dir / "microdados_enem_*.parquet",
            "gold_cleaned": g_dir / "cleaned" / "microdados_enem_*_clean.parquet",
            "gold_classes": g_dir / "classes" / "classes_enem_*.parquet",
            "gold_tb_notas": g_dir / "tb_notas.parquet",
            "gold_tb_notas_stats": g_dir / "tb_notas_stats.parquet",
            "gold_tb_notas_geo": g_dir / "tb_notas_geo.parquet",
            "gold_tb_notas_geo_uf": g_dir / "tb_notas_geo_uf.parquet",
            "gold_tb_notas_histogram": g_dir / "tb_notas_histogram.parquet",
            "gold_tb_socio_economico": g_dir / "tb_socio_economico.parquet",
            "gold_tb_media_uf": g_dir / "tb_media_uf.parquet",
            "gold_tb_media_municipal": g_dir / "tb_media_municipal.parquet",
            "dim_municipio": g_dir / "dim_municipio.parquet",
        }

        optional_views = {
            "gold_tb_socio_economico",
            "gold_tb_media_uf",
            "gold_tb_media_municipal",
            "dim_municipio",
        }
        registered, skipped_optional = [], []

        for view_name, path in views.items():
            has_wildcard = any(ch in path.name for ch in ("*", "?", "["))
            matches = (
                list(path.parent.glob(path.name))
                if has_wildcard
                else ([path] if path.exists() else [])
            )

            if not matches:
                if view_name in optional_views:
                    skipped_optional.append(view_name)
                    continue
                raise FileNotFoundError(
                    f"Parquet não encontrado para view {view_name}: {path}"
                )

            # SECURITY: view_name e path são controlados internamente,
            # não vêm de input do usuário - SQL injection não é possível aqui.
            sql = (
                f"CREATE OR REPLACE VIEW {view_name} AS "  # nosec B608
                f"SELECT * FROM read_parquet('{path.as_posix()}')"
            )
            conn.execute(sql)
            registered.append(view_name)

        logger.info(f"Views registradas: {registered}")
        if skipped_optional:
            logger.info(f"Views opcionais ignoradas: {skipped_optional}")


# Compatibilidade com código antigo
def get_duckdb_conn(
    db_path: Optional[Path | str] = None, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    """Wrapper de compatibilidade para obter conexão DuckDB."""
    agent = DuckDBAgent(db_path, read_only=read_only)
    return agent.get_connection()


def register_parquet_views(_conn: duckdb.DuckDBPyConnection) -> None:
    """Função legada para registrar views (mantida para compatibilidade)."""
    pass
