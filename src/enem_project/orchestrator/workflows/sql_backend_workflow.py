from __future__ import annotations

from pathlib import Path

from ...infra.db import get_duckdb_conn, register_parquet_views, default_db_path
from ...infra.data_quality import assert_dashboard_data_checks
from ...infra.logging import logger


def init_sql_backend(
    *,
    materialize_dashboard_tables: bool = True,
) -> Path:
    """
    Inicializa o backend SQL baseado em DuckDB para consumo analítico.

    Passos:
        1. Abre (ou cria) o arquivo enem.duckdb no diretório de dados.
        2. Registra views sobre os Parquets de silver/gold, incluindo:
           - gold_tb_notas
           - gold_tb_notas_stats
           - gold_tb_notas_geo
        3. Opcionalmente materializa tabelas físicas a partir dessas views,
           facilitando o consumo por ferramentas externas que esperam
           tabelas estáveis.

    Retorna o caminho do arquivo DuckDB criado/atualizado.
    """
    db_path = default_db_path()
    conn = get_duckdb_conn(db_path)
    register_parquet_views(conn)

    if materialize_dashboard_tables:
        logger.info(
            "[sql-backend] Materializando tabelas de dashboard a partir dos Parquets gold (tb_notas*, tb_notas_stats*, tb_notas_geo*).",
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE tb_notas AS
            SELECT * FROM gold_tb_notas
            """,
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE tb_notas_stats AS
            SELECT * FROM gold_tb_notas_stats
            """,
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE tb_notas_geo AS
            SELECT * FROM gold_tb_notas_geo
            """,
        )
        logger.success(
            "[sql-backend] Tabelas tb_notas, tb_notas_stats e tb_notas_geo materializadas em %s.",
            db_path,
        )
        # Aplica checks de qualidade de dados mínimos como quality gate.
        assert_dashboard_data_checks(conn)
    else:
        logger.info(
            "[sql-backend] Somente views registradas em DuckDB; consumo via gold_tb_*.",
        )

    conn.close()
    return db_path
