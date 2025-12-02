from __future__ import annotations

from pathlib import Path
from typing import Iterable

from enem_project.config.settings import settings
from ...data.silver_to_gold import (
    build_tb_notas_stats_from_cleaned,
    build_tb_notas_geo_from_cleaned,
    build_tb_notas_geo_uf_from_cleaned,
    build_tb_notas_histogram_from_cleaned,
    build_tb_socio_economico_from_cleaned,
)
from ...infra.db_agent import DuckDBAgent
from ...infra.data_quality import assert_dashboard_data_checks
from ...infra.logging import logger


def run_sql_backend_workflow(
    *,
    materialize_dashboard_tables: bool = True,
    years: Iterable[int] | None = None,
) -> Path:
    """
    Executa o workflow completo do backend SQL, que materializa as tabelas
    Gold e as carrega no DuckDB para consumo analítico.

    Passos:
        1. Gera os Parquets agregados (gold) a partir dos dados limpos.
        2. Inicializa o DuckDBAgent (com guardrails e logs).
        3. Registra views sobre os Parquets de silver/gold via Agente.
        4. Executa script SQL externalizado para materializar tabelas físicas.
        5. Executa quality checks nos dados materializados.

    Retorna o caminho do arquivo DuckDB criado/atualizado.
    """
    target_years = tuple(sorted(set(years))) if years is not None else settings.YEARS
    agent = DuckDBAgent(read_only=False)
    db_path = agent.db_path

    # Falha rápido se já existir lock de escrita no arquivo DuckDB.
    # Mantemos a conexão aberta para garantir posse do lock durante o workflow.
    agent.get_connection()

    # Passo 1: Construir tabelas Gold a partir da Silver (cleaned)
    logger.info(
        "[workflow-sql] Iniciando construção das tabelas Gold (agregações) para anos: {}",
        target_years,
    )
    build_tb_notas_stats_from_cleaned(target_years)
    build_tb_notas_geo_from_cleaned(target_years)
    build_tb_notas_geo_uf_from_cleaned(target_years)
    build_tb_notas_histogram_from_cleaned(target_years)
    build_tb_socio_economico_from_cleaned(target_years)
    logger.success("[workflow-sql] Tabelas Gold (Parquet) geradas com sucesso.")

    # Passos 2-5: Carregar e materializar no DuckDB usando Agente
    try:
        agent.register_parquet_views()

        if materialize_dashboard_tables:
            logger.info(
                "[workflow-sql] Materializando tabelas de dashboard a partir de script SQL externo.",
            )
            
            # Carrega script SQL externalizado
            sql_path = Path(__file__).parents[2] / "sql" / "marts" / "materialize_dashboard_tables.sql"
            if not sql_path.exists():
                 raise FileNotFoundError(f"Script SQL não encontrado em: {sql_path}")
            
            sql_script = sql_path.read_text(encoding="utf-8")
            agent.execute_script(sql_script)

            logger.success(
                "[workflow-sql] Tabelas do dashboard materializadas em {}.",
                db_path,
            )
            # Aplica checks de qualidade de dados mínimos como quality gate.
            # Passamos a conexão crua para a função de check legado
            assert_dashboard_data_checks(agent._get_conn())
        else:
            logger.info(
                "[sql-backend] Somente views registradas em DuckDB; consumo via gold_tb_*.",
            )
    finally:
        agent.close()

    return db_path
