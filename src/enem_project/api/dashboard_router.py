from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from .dependencies import duckdb_readonly_conn
from .schemas import TbNotasGeoRow, TbNotasStatsRow


router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


@router.get(
    "/anos-disponiveis",
    response_model=List[int],
    summary="Lista de anos disponíveis nas tabelas de dashboard.",
)
def get_anos_disponiveis() -> List[int]:
    """
    Retorna todos os anos disponíveis nas tabelas de dashboard, conforme
    materializadas no backend SQL. A consulta é feita diretamente sobre
    tb_notas_stats para refletir o recorte efetivamente pronto para consumo.
    """
    sql = """
        SELECT DISTINCT ANO
        FROM tb_notas_stats
        ORDER BY ANO
    """

    with duckdb_readonly_conn() as conn:
        try:
            rows = conn.execute(sql).fetchall()
        except Exception as exc:  # pragma: no cover - proteção defensiva
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao consultar anos disponíveis: {exc}",
            ) from exc

    return [int(row[0]) for row in rows]


@router.get(
    "/notas/stats",
    response_model=List[TbNotasStatsRow],
    summary="Estatísticas anuais de notas (tb_notas_stats).",
)
def get_notas_stats(
    ano_inicio: Optional[int] = Query(
        None,
        description="Ano inicial (inclusive) para filtrar as estatísticas.",
    ),
    ano_fim: Optional[int] = Query(
        None,
        description="Ano final (inclusive) para filtrar as estatísticas.",
    ),
) -> List[TbNotasStatsRow]:
    """
    Retorna as estatísticas descritivas anuais das notas, conforme
    tabela tb_notas_stats da camada gold.
    """
    where_clauses: list[str] = []
    params: list[object] = []

    if ano_inicio is not None:
        where_clauses.append("ANO >= ?")
        params.append(ano_inicio)
    if ano_fim is not None:
        where_clauses.append("ANO <= ?")
        params.append(ano_fim)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sql = f"""
        SELECT *
        FROM tb_notas_stats
        {where_sql}
        ORDER BY ANO
    """

    with duckdb_readonly_conn() as conn:
        try:
            rows = conn.execute(sql, params).fetchall()
            columns = [d[0] for d in conn.description]
        except Exception as exc:  # pragma: no cover - proteção defensiva
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao consultar tb_notas_stats: {exc}",
            ) from exc

    return [TbNotasStatsRow(**dict(zip(columns, row))) for row in rows]


@router.get(
    "/notas/geo",
    response_model=List[TbNotasGeoRow],
    summary="Notas agregadas por ano/UF/município (tb_notas_geo).",
)
def get_notas_geo(
    ano: Optional[int] = Query(
        None,
        description="Ano de referência. Se omitido, retorna todos os anos.",
    ),
    uf: Optional[str] = Query(
        None,
        description="Sigla da UF da prova (SG_UF_PROVA) para filtrar.",
        min_length=2,
        max_length=2,
    ),
    min_count: int = Query(
        30,
        ge=0,
        description=(
            "Filtro mínimo de participantes (NOTA_*_count) para reduzir "
            "ruído em municípios com amostras muito pequenas."
        ),
    ),
    limit: int = Query(
        5000,
        ge=1,
        le=100_000,
        description="Limite máximo de linhas retornadas.",
    ),
    page: int = Query(
        1,
        ge=1,
        description=(
            "Número da página para paginação simples, "
            "combinado com o parâmetro 'limit'."
        ),
    ),
) -> List[TbNotasGeoRow]:
    """
    Retorna agregados de notas por ano/UF/município a partir da tabela
    tb_notas_geo materializada no backend SQL.
    """
    where_clauses: list[str] = []
    params: list[object] = []

    if ano is not None:
        where_clauses.append("ANO = ?")
        params.append(ano)
    if uf is not None:
        where_clauses.append("SG_UF_PROVA = ?")
        params.append(uf.upper())
    if min_count > 0:
        # Aplica o filtro de amostra mínima em todas as áreas de forma conservadora.
        where_clauses.append(
            "NOTA_CIENCIAS_NATUREZA_count >= ? "
            "AND NOTA_CIENCIAS_HUMANAS_count >= ? "
            "AND NOTA_LINGUAGENS_CODIGOS_count >= ? "
            "AND NOTA_MATEMATICA_count >= ? "
            "AND NOTA_REDACAO_count >= ?"
        )
        params.extend([min_count] * 5)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sql = f"""
        SELECT
            ANO,
            SG_UF_PROVA,
            CAST(CO_MUNICIPIO_PROVA AS VARCHAR) AS CO_MUNICIPIO_PROVA,
            NO_MUNICIPIO_PROVA,
            NOTA_CIENCIAS_NATUREZA_count,
            NOTA_CIENCIAS_NATUREZA_mean,
            NOTA_CIENCIAS_HUMANAS_count,
            NOTA_CIENCIAS_HUMANAS_mean,
            NOTA_LINGUAGENS_CODIGOS_count,
            NOTA_LINGUAGENS_CODIGOS_mean,
            NOTA_MATEMATICA_count,
            NOTA_MATEMATICA_mean,
            NOTA_REDACAO_count,
            NOTA_REDACAO_mean
        FROM tb_notas_geo
        {where_sql}
        ORDER BY ANO, SG_UF_PROVA, NO_MUNICIPIO_PROVA
        LIMIT ? OFFSET ?
    """
    offset = (page - 1) * limit
    params.extend([limit, offset])

    with duckdb_readonly_conn() as conn:
        try:
            rows = conn.execute(sql, params).fetchall()
            columns = [d[0] for d in conn.description]
        except Exception as exc:  # pragma: no cover - proteção defensiva
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao consultar tb_notas_geo: {exc}",
            ) from exc

    return [TbNotasGeoRow(**dict(zip(columns, row))) for row in rows]
