"""
Módulo para geração de tabelas dimensionais.
"""

import duckdb
import pandas as pd
from loguru import logger
from enem_project.config.settings import settings

# Caminho para a tabela dimensão
DATA_DIR = settings.DATA_DIR
DIM_MUNICIPIO_PATH = DATA_DIR / "02_gold" / "dim_municipio.parquet"

# Mapeamento oficial IBGE: Código UF → Sigla UF
# Os primeiros 2 dígitos do CO_MUNICIPIO correspondem ao código da UF
IBGE_UF_MAP = {
    11: "RO",
    12: "AC",
    13: "AM",
    14: "RR",
    15: "PA",
    16: "AP",
    17: "TO",
    21: "MA",
    22: "PI",
    23: "CE",
    24: "RN",
    25: "PB",
    26: "PE",
    27: "AL",
    28: "SE",
    29: "BA",
    31: "MG",
    32: "ES",
    33: "RJ",
    35: "SP",
    41: "PR",
    42: "SC",
    43: "RS",
    50: "MS",
    51: "MT",
    52: "GO",
    53: "DF",
}


def build_dim_municipio(years: list[int] | None = None) -> pd.DataFrame:
    """
    Gera a tabela dimensão `dim_municipio` a partir dos dados limpos.

    Usa o código IBGE do município para derivar a UF correta,
    evitando dependência de dados de prova que podem ter inconsistências.
    """
    if years is None:
        years = list(range(2009, 2025))

    logger.info("Iniciando geração de dim_municipio...")

    parquet_files = []
    for year in years:
        path = (
            DATA_DIR / "02_gold" / "cleaned" / f"microdados_enem_{year}_clean.parquet"
        )
        if path.exists():
            parquet_files.append(str(path))
        else:
            logger.debug(f"Arquivo não encontrado: {path}")

    if not parquet_files:
        logger.warning("Nenhum arquivo de dados encontrado para dimensão.")
        return pd.DataFrame()

    # SECURITY: parquet_files é construído internamente, não vem de input
    # do usuário - SQL injection não é possível aqui.
    query = f"""
    WITH all_municipios AS (
        SELECT
            CAST(CO_MUNICIPIO_PROVA AS BIGINT) as CO_MUNICIPIO_PROVA,
            NO_MUNICIPIO_PROVA,
            COUNT(*) as frequency
        FROM read_parquet({parquet_files})
        WHERE CO_MUNICIPIO_PROVA IS NOT NULL
          AND NO_MUNICIPIO_PROVA IS NOT NULL
        GROUP BY 1, 2
    ),
    ranked_names AS (
        SELECT
            CO_MUNICIPIO_PROVA,
            NO_MUNICIPIO_PROVA,
            ROW_NUMBER() OVER (
                PARTITION BY CO_MUNICIPIO_PROVA
                ORDER BY frequency DESC, NO_MUNICIPIO_PROVA ASC
            ) as rn
        FROM all_municipios
    )
    SELECT
        CO_MUNICIPIO_PROVA,
        NO_MUNICIPIO_PROVA,
        CAST(SUBSTRING(CAST(CO_MUNICIPIO_PROVA AS VARCHAR), 1, 2) AS INT)
            as UF_CODE
    FROM ranked_names
    WHERE rn = 1
    ORDER BY CO_MUNICIPIO_PROVA
    """  # nosec B608

    try:
        df_dim = duckdb.sql(query).df()

        # Mapear código UF para sigla
        df_dim["SG_UF_PROVA"] = df_dim["UF_CODE"].map(IBGE_UF_MAP)
        df_dim = df_dim.drop(columns=["UF_CODE"])

        # Remover linhas com UF não mapeada
        invalid = df_dim["SG_UF_PROVA"].isna()
        if invalid.any():
            logger.warning(
                f"{invalid.sum()} municípios com código UF inválido removidos."
            )
            df_dim = df_dim[~invalid]

        # Validar unicidade
        if df_dim["CO_MUNICIPIO_PROVA"].duplicated().any():
            logger.error("Chaves duplicadas em dim_municipio!")
            raise ValueError("Duplicate Keys in dim_municipio")

        logger.info(
            f"Salvando dim_municipio com {len(df_dim)} registros "
            f"em {DIM_MUNICIPIO_PATH}"
        )
        df_dim.to_parquet(DIM_MUNICIPIO_PATH, index=False)

        return df_dim

    except Exception as e:
        logger.error(f"Erro ao gerar dim_municipio: {e}")
        raise
