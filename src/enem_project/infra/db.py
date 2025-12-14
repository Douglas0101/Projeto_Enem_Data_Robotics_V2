from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb

from ..config.paths import gold_dir, silver_dir
from .logging import logger


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
        db_path: caminho do arquivo .duckdb (opcional; usa default_db_path se None).
        read_only: quando True, abre a conexão em modo somente leitura.
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
        - silver_microdados      → data/01_silver/microdados_enem_*.parquet (tudo)
        - gold_cleaned           → data/02_gold/cleaned/*.parquet
        - gold_classes           → data/02_gold/classes/classes_enem_*.parquet
        - gold_tb_notas          → data/02_gold/tb_notas.parquet
        - gold_tb_notas_stats    → data/02_gold/tb_notas_stats.parquet
        - gold_tb_notas_geo      → data/02_gold/tb_notas_geo.parquet
    """
    s_dir = silver_dir()
    g_dir = gold_dir()

    # Views agregadas sobre silver/gold (podem não existir em todos os ambientes).
    query_silver = f"""
        CREATE OR REPLACE VIEW silver_microdados AS
        SELECT * FROM read_parquet('{(s_dir / "microdados_enem_*.parquet").as_posix()}')
        """  # nosec B608
    conn.execute(query_silver)

    query_cleaned = f"""
        CREATE OR REPLACE VIEW gold_cleaned AS
        SELECT * FROM read_parquet('{(g_dir / "cleaned" / "microdados_enem_*_clean.parquet").as_posix()}')
        """  # nosec B608
    conn.execute(query_cleaned)

    query_classes = f"""
        CREATE OR REPLACE VIEW gold_classes AS
        SELECT * FROM read_parquet('{(g_dir / "classes" / "classes_enem_*.parquet").as_posix()}')
        """  # nosec B608
    conn.execute(query_classes)

    # Views diretamente mapeadas para as tabelas do dashboard.
    query_notas = f"""
        CREATE OR REPLACE VIEW gold_tb_notas AS
        SELECT * FROM read_parquet('{(g_dir / "tb_notas.parquet").as_posix()}')
        """  # nosec B608
    conn.execute(query_notas)

    query_stats = f"""
        CREATE OR REPLACE VIEW gold_tb_notas_stats AS
        SELECT * FROM read_parquet('{(g_dir / "tb_notas_stats.parquet").as_posix()}')
        """  # nosec B608
    conn.execute(query_stats)

    query_geo = f"""
        CREATE OR REPLACE VIEW gold_tb_notas_geo AS
        SELECT * FROM read_parquet('{(g_dir / "tb_notas_geo.parquet").as_posix()}')
        """  # nosec B608
    conn.execute(query_geo)

    query_geo_uf = f"""
        CREATE OR REPLACE VIEW gold_tb_notas_geo_uf AS
        SELECT * FROM read_parquet('{(g_dir / "tb_notas_geo_uf.parquet").as_posix()}')
        """  # nosec B608
    conn.execute(query_geo_uf)

    query_histogram = f"""
        CREATE OR REPLACE VIEW gold_tb_notas_histogram AS
        SELECT * FROM read_parquet('{(g_dir / "tb_notas_histogram.parquet").as_posix()}')
        """  # nosec B608
    conn.execute(query_histogram)

    query_socio = f"""
        CREATE OR REPLACE VIEW gold_tb_socio_economico AS
        SELECT * FROM read_parquet('{(g_dir / "tb_socio_economico.parquet").as_posix()}')
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

    logger.info(
        "Views DuckDB registradas para silver/gold (incluindo tabelas de dashboard)."
    )
