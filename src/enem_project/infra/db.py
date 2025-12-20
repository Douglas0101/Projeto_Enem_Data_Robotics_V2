"""Módulo de interface com DuckDB para conexão e execução de queries."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb

from enem_project.config.paths import gold_dir, silver_dir
from enem_project.infra.logging import logger


def default_db_path() -> Path:
    """
    Caminho padrão do banco DuckDB usado para consultas SQL sobre
    as camadas silver/gold.
    """
    # Mantém o banco ao lado das camadas de dados para facilitar transporte.
    return gold_dir().parent / "enem.duckdb"


def get_duckdb_conn(
    db_path: Optional[Path | str] = None,
    *,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    """
    Abre (ou cria) uma conexão DuckDB para consultas SQL.

    Parâmetros:
        db_path: caminho do arquivo .duckdb (opcional; usa
            default_db_path se None).
        read_only: quando True, abre conexão em modo somente leitura.
    """
    path = Path(db_path) if db_path is not None else default_db_path()
    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Conectando ao DuckDB: {} (read_only={})",
        path,
        read_only,
    )
    return duckdb.connect(path.as_posix(), read_only=read_only)


def register_parquet_views(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Registra views SQL convenientes sobre os principais Parquets de
    interesse analítico. As views expõem os mesmos nomes de colunas
    esperados pelos dashboards.

    Views criadas (se os arquivos existirem):
        - silver_microdados   → data/01_silver/microdados_enem_*.parquet
        - gold_cleaned        → data/02_gold/cleaned/*.parquet
        - gold_classes        → data/02_gold/classes/*.parquet
        - gold_tb_notas       → data/02_gold/tb_notas.parquet
        - gold_tb_notas_stats → data/02_gold/tb_notas_stats.parquet
        - gold_tb_notas_geo   → data/02_gold/tb_notas_geo.parquet
    """
    s_dir = silver_dir()
    g_dir = gold_dir()

    # Views agregadas sobre silver/gold (podem não existir em ambientes).
    query_silver = f"""
        CREATE OR REPLACE VIEW silver_microdados AS
        SELECT * FROM read_parquet(
            '{(s_dir / "microdados_enem_*.parquet").as_posix()}'
        )
        """  # nosec B608
    conn.execute(query_silver)

    cleaned_path = g_dir / "cleaned" / "microdados_enem_*_clean.parquet"
    query_cleaned = f"""
        CREATE OR REPLACE VIEW gold_cleaned AS
        SELECT * FROM read_parquet('{cleaned_path.as_posix()}')
        """  # nosec B608
    conn.execute(query_cleaned)

    classes_path = g_dir / "classes" / "classes_enem_*.parquet"
    query_classes = f"""
        CREATE OR REPLACE VIEW gold_classes AS
        SELECT * FROM read_parquet('{classes_path.as_posix()}')
        """  # nosec B608
    conn.execute(query_classes)

    # Views diretamente mapeadas para as tabelas do dashboard.
    notas_path = g_dir / "tb_notas.parquet"
    query_notas = f"""
        CREATE OR REPLACE VIEW gold_tb_notas AS
        SELECT * FROM read_parquet('{notas_path.as_posix()}')
        """  # nosec B608
    conn.execute(query_notas)

    stats_path = g_dir / "tb_notas_stats.parquet"
    query_stats = f"""
        CREATE OR REPLACE VIEW gold_tb_notas_stats AS
        SELECT * FROM read_parquet('{stats_path.as_posix()}')
        """  # nosec B608
    conn.execute(query_stats)

    geo_path = g_dir / "tb_notas_geo.parquet"
    query_geo = f"""
        CREATE OR REPLACE VIEW gold_tb_notas_geo AS
        SELECT * FROM read_parquet('{geo_path.as_posix()}')
        """  # nosec B608
    conn.execute(query_geo)

    geo_uf_path = g_dir / "tb_notas_geo_uf.parquet"
    query_geo_uf = f"""
        CREATE OR REPLACE VIEW gold_tb_notas_geo_uf AS
        SELECT * FROM read_parquet('{geo_uf_path.as_posix()}')
        """  # nosec B608
    conn.execute(query_geo_uf)

    histogram_path = g_dir / "tb_notas_histogram.parquet"
    query_histogram = f"""
        CREATE OR REPLACE VIEW gold_tb_notas_histogram AS
        SELECT * FROM read_parquet('{histogram_path.as_posix()}')
        """  # nosec B608
    conn.execute(query_histogram)

    socio_path = g_dir / "tb_socio_economico.parquet"
    query_socio = f"""
        CREATE OR REPLACE VIEW gold_tb_socio_economico AS
        SELECT * FROM read_parquet('{socio_path.as_posix()}')
        """  # nosec B608
    conn.execute(query_socio)

    # Tabela dimensional de municípios (único por código IBGE)
    dim_municipio_path = g_dir / "dim_municipio.parquet"
    if dim_municipio_path.exists():
        query_dim_mun = f"""
            CREATE OR REPLACE VIEW dim_municipio AS
            SELECT * FROM read_parquet('{dim_municipio_path.as_posix()}')
            """  # nosec B608
        conn.execute(query_dim_mun)
        logger.info("View dim_municipio registrada.")

    # Tabela de distribuição de notas por UF (pré-calculada)
    media_uf_path = g_dir / "tb_media_uf.parquet"
    if media_uf_path.exists():
        query_media_uf = f"""
            CREATE OR REPLACE VIEW gold_tb_media_uf AS
            SELECT * FROM read_parquet('{media_uf_path.as_posix()}')
            """  # nosec B608
        conn.execute(query_media_uf)
        logger.info("View gold_tb_media_uf registrada.")

    logger.info(
        "Views DuckDB registradas para silver/gold " "(incluindo tabelas de dashboard)."
    )
