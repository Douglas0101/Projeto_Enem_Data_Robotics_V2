from functools import lru_cache
from typing import List, Annotated

from fastapi import APIRouter, HTTPException, Query

from enem_project.infra.db_agent import DuckDBAgent
from enem_project.infra.logging import logger
from .schemas import TbNotasGeoRow, TbNotasStatsRow, TbNotasGeoUfRow, TbNotasHistogramRow, TbSocioRaceRow, TbSocioIncomeRow


router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])
db_agent = DuckDBAgent(read_only=True) # Global instance for read-only queries


@router.get(
    "/advanced/socioeconomic/race",
    response_model=List[TbSocioRaceRow],
    summary="Médias de notas por Cor/Raça (Real Data).",
)
@lru_cache(maxsize=32)
def get_socioeconomic_race(
    ano: Annotated[int, Query(description="Ano de referência.")],
    uf: Annotated[str | None, Query(
        description="Sigla da UF da prova (SG_UF_PROVA) para filtrar.",
        min_length=2,
        max_length=2,
    )] = None,
) -> List[TbSocioRaceRow]:
    """
    Retorna a média das notas agrupadas por autodeclaração de cor/raça.
    Utiliza a tabela gold_classes (ou silver_microdados) para cálculo on-the-fly
    sobre o ano selecionado.
    """
    # Mapeamento IBGE
    # 0: Não declarado, 1: Branca, 2: Preta, 3: Parda, 4: Amarela, 5: Indígena
    
    where_clauses: list[str] = ["ANO = ?"]
    params: list[object] = [ano]

    if uf:
        where_clauses.append("SG_UF_PROVA = ?")
        params.append(uf.upper())

    where_sql = "WHERE " + " AND ".join(where_clauses)
    
    sql = f"""
        SELECT 
            TP_COR_RACA,
            AVG(NOTA_MATEMATICA) as NOTA_MATEMATICA,
            AVG(NOTA_CIENCIAS_NATUREZA) as NOTA_CIENCIAS_NATUREZA,
            AVG(NOTA_CIENCIAS_HUMANAS) as NOTA_CIENCIAS_HUMANAS,
            AVG(NOTA_LINGUAGENS_CODIGOS) as NOTA_LINGUAGENS_CODIGOS,
            AVG(NOTA_REDACAO) as NOTA_REDACAO,
            COUNT(*) as COUNT
        FROM gold_classes
        {where_sql}
        GROUP BY TP_COR_RACA
        HAVING COUNT(*) > 100
    """
    
    race_map = {
        0: "Não Declarado",
        1: "Branca",
        2: "Preta",
        3: "Parda",
        4: "Amarela",
        5: "Indígena",
        6: "Não Disp."
    }

    conn = db_agent._get_conn()
    try:
        rows, columns = db_agent.run_query(sql, params)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar dados socioeconômicos: {exc}",
        ) from exc

    result = []
    for row in rows:
        tp_raca = row[0]
        # Handle NULL or None as "Não Disp." (6) or use existing map
        if tp_raca is None:
             label = race_map[6]
        else:
             label = race_map.get(tp_raca, f"Outros ({tp_raca})")
             
        result.append(TbSocioRaceRow(
            RACA=label,
            NOTA_MATEMATICA=row[1],
            NOTA_CIENCIAS_NATUREZA=row[2],
            NOTA_CIENCIAS_HUMANAS=row[3],
            NOTA_LINGUAGENS_CODIGOS=row[4],
            NOTA_REDACAO=row[5],
            COUNT=row[6]
        ))
    
    return sorted(result, key=lambda x: x.COUNT, reverse=True)


@router.get(
    "/advanced/socioeconomic/income",
    response_model=List[TbSocioIncomeRow],
    summary="Distribuição de Notas por Renda (Dados Reais - Dumbbell Chart).",
)
@lru_cache(maxsize=32)
def get_socioeconomic_income(
    ano: Annotated[int, Query(description="Ano de referência.")],
) -> List[TbSocioIncomeRow]:
    """
    Retorna estatísticas de dispersão (Min, Q1, Mediana, Q3, Max) da Nota Geral
    por classe de renda (Q006), filtrando apenas presentes.
    Dados da tabela gold 'tb_socio_economico'.
    """
    sql = """
        SELECT CLASSE, LOW, Q1, MEDIAN, Q3, HIGH
        FROM tb_socio_economico
        WHERE ANO = ?
        ORDER BY CLASSE
    """
    
    conn = db_agent._get_conn()
    try:
        rows, columns = db_agent.run_query(sql, [ano])
    except Exception as exc:
        # Fallback se a tabela não existir ainda (antes do primeiro ETL novo)
        logger.warning(f"Erro ao ler tb_socio_economico: {exc}")
        return []

    return [TbSocioIncomeRow(CLASSE=row[0], LOW=row[1], Q1=row[2], MEDIAN=row[3], Q3=row[4], HIGH=row[5]) for row in rows]


@router.get(
    "/anos-disponiveis",
    response_model=List[int],
    summary="Lista de anos disponíveis nas tabelas de dashboard.",
)
@lru_cache(maxsize=1) # Poucos anos, cache forte
def get_anos_disponiveis() -> List[int]:
    """
    Retorna todos os anos disponíveis nas tabelas de dashboard, conforme
    materializadas no backend SQL. A consulta é feita diretamente sobre
    tb_notas_stats e filtra apenas anos que possuam notas carregadas
    (evita expor anos sem dados, como 2024 enquanto o INEP não publica
    as notas).
    """
    sql = """
        SELECT DISTINCT ANO
        FROM tb_notas_stats
        WHERE (
            COALESCE(NOTA_CIENCIAS_NATUREZA_count, 0)
          + COALESCE(NOTA_CIENCIAS_HUMANAS_count, 0)
          + COALESCE(NOTA_LINGUAGENS_CODIGOS_count, 0)
          + COALESCE(NOTA_MATEMATICA_count, 0)
          + COALESCE(NOTA_REDACAO_count, 0)
        ) > 0
        ORDER BY ANO
    """

    conn = db_agent._get_conn()
    try:
        rows, columns = db_agent.run_query(sql)
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
@lru_cache(maxsize=32)
def get_notas_stats(
    ano_inicio: Annotated[int | None, Query(
        description="Ano inicial (inclusive) para filtrar as estatísticas.",
    )] = None,
    ano_fim: Annotated[int | None, Query(
        description="Ano final (inclusive) para filtrar as estatísticas.",
    )] = None,
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

    conn = db_agent._get_conn()
    try:
        rows, columns = db_agent.run_query(sql, params)
    except Exception as exc:
        # Se falhar (ex: ano sem partição), retorna lista vazia para não quebrar o frontend
        logger.warning(f"Consulta a tb_notas_stats falhou (possível ano inexistente): {exc}")
        return []

    results = []
    for row in rows:
        try:
            results.append(TbNotasStatsRow(**dict(zip(columns, row))))
        except Exception as e:
            # Pula linhas com dados inválidos (ex: NULL em campo obrigatório) para não quebrar o dash
            logger.warning(f"Dados inválidos em tb_notas_stats (pulando linha): {e}")
            continue
            
    return results


@router.get(
    "/notas/geo",
    response_model=List[TbNotasGeoRow],
    summary="Notas agregadas por ano/UF/município (tb_notas_geo).",
)
@lru_cache(maxsize=32)
def get_notas_geo(
    ano: Annotated[int | None, Query(
        description="Ano de referência. Se omitido, retorna todos os anos.",
    )] = None,
    uf: Annotated[str | None, Query(
        description="Sigla da UF da prova (SG_UF_PROVA) para filtrar.",
        min_length=2,
        max_length=2,
    )] = None,
    min_count: Annotated[int, Query(
        ge=0,
        description=(
            "Filtro mínimo de participantes (NOTA_*_count) para reduzir "
            "ruído em municípios com amostras muito pequenas."
        ),
    )] = 30,
    limit: Annotated[int, Query(
        ge=1,
        le=100_000,
        description="Limite máximo de linhas retornadas.",
    )] = 5000,
    page: Annotated[int, Query(
        ge=1,
        description=(
            "Número da página para paginação simples, "
            "combinado com o parâmetro 'limit'."
        ),
    )] = 1,
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

    conn = db_agent._get_conn()
    try:
        rows, columns = db_agent.run_query(sql, params)
    except Exception as exc:
        # Se falhar (ex: ano sem partição), retorna lista vazia para não quebrar o frontend
        logger.warning(f"Consulta a tb_notas_geo falhou (possível ano inexistente): {exc}")
        return []

    results = []
    for row in rows:
        try:
            results.append(TbNotasGeoRow(**dict(zip(columns, row))))
        except Exception as e:
            logger.warning(f"Dados inválidos em tb_notas_geo (pulando linha): {e}")
            continue
    return results


@router.get(
    "/notas/geo-uf",
    response_model=List[TbNotasGeoUfRow],
    summary="Notas agregadas por ano/UF (tb_notas_geo_uf).",
)
@lru_cache(maxsize=32)
def get_notas_geo_uf(
    ano: Annotated[int | None, Query(description="Ano de referência. Se omitido, retorna todos os anos.")] = None,
    min_inscritos: Annotated[int, Query(
        ge=0,
        description="Filtro mínimo de inscritos para incluir a UF no resultado.",
    )] = 100,
    uf: Annotated[str | None, Query(
        description="Sigla da UF da prova (SG_UF_PROVA) para filtrar.",
        min_length=2,
        max_length=2,
    )] = None,
) -> List[TbNotasGeoUfRow]:
    """
    Retorna agregados de notas por ano/UF a partir da tabela
    tb_notas_geo_uf materializada no backend SQL.
    """
    where_clauses: list[str] = ["INSCRITOS >= ?"]
    params: list[object] = [min_inscritos]

    if ano is not None:
        where_clauses.append("ANO = ?")
        params.append(ano)
        
    if uf is not None:
        where_clauses.append("SG_UF_PROVA = ?")
        params.append(uf.upper())

    where_sql = "WHERE " + " AND ".join(where_clauses)

    sql = f"""
        SELECT *
        FROM tb_notas_geo_uf
        {where_sql}
        ORDER BY ANO, SG_UF_PROVA
    """

    conn = db_agent._get_conn()
    try:
        rows, columns = db_agent.run_query(sql, params)
    except Exception as exc:
        # Se falhar (ex: ano sem partição), retorna lista vazia para não quebrar o frontend
        logger.warning(f"Consulta a tb_notas_geo_uf falhou (possível ano inexistente): {exc}")
        return []

    required_fields = list(TbNotasGeoUfRow.model_fields.keys())

    results = []
    for row in rows:
        try:
            record = dict(zip(columns, row))
            # Preenche campos ausentes e converte contagens para int
            for field in required_fields:
                if field not in record:
                    record[field] = None
            for field in ("INSCRITOS", "NOTA_CIENCIAS_NATUREZA_count", "NOTA_CIENCIAS_HUMANAS_count",
                          "NOTA_LINGUAGENS_CODIGOS_count", "NOTA_MATEMATICA_count", "NOTA_REDACAO_count"):
                if record.get(field) is not None:
                    try:
                        record[field] = int(record[field])
                    except Exception:
                        pass
            results.append(TbNotasGeoUfRow(**record))
        except Exception as e:
            logger.warning(f"Dados inválidos em tb_notas_geo_uf (pulando linha): {e}")
            continue
    return results


@router.get(
    "/notas/histograma",
    response_model=List[TbNotasHistogramRow],
    summary="Dados para histograma de notas (tb_notas_histogram).",
)
@lru_cache(maxsize=32)
def get_notas_histograma(
    ano: Annotated[int, Query(description="Ano de referência.")],
    disciplina: Annotated[str, Query(description="Disciplina para o histograma.")],
) -> List[TbNotasHistogramRow]:
    """
    Retorna dados pré-calculados para a construção de histogramas de notas
    a partir da tabela tb_notas_histogram.
    """
    sql = """
        SELECT ANO, DISCIPLINA, BIN_START, BIN_END, CONTAGEM
        FROM tb_notas_histogram
        WHERE ANO = ? AND DISCIPLINA = ?
        ORDER BY BIN_START
    """
    params = [ano, disciplina]

    conn = db_agent._get_conn()
    try:
        rows, columns = db_agent.run_query(sql, params)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar tb_notas_histogram: {exc}",
        ) from exc

    return [TbNotasHistogramRow(**dict(zip(columns, row))) for row in rows]


@router.get(
    "/advanced/radar",
    summary="Dados para o gráfico de radar comparativo (UF vs BR vs Melhor UF).",
)
@lru_cache(maxsize=32)
def get_radar_data(
    ano: Annotated[int, Query(description="Ano de referência.")],
    uf: Annotated[str | None, Query(
        description="Sigla da UF para comparação (opcional).",
        min_length=2,
        max_length=2,
    )] = None,
):
    """
    Retorna dados formatados para o gráfico de radar, comparando:
    1. Média da UF selecionada (se informada)
    2. Média Nacional (BR)
    3. Média da melhor UF em cada disciplina (Benchmark)
    """
    disciplinas = {
        "NOTA_MATEMATICA_mean": "Matemática",
        "NOTA_CIENCIAS_NATUREZA_mean": "Ciências da Natureza",
        "NOTA_CIENCIAS_HUMANAS_mean": "Ciências Humanas",
        "NOTA_LINGUAGENS_CODIGOS_mean": "Linguagens e Códigos",
        "NOTA_REDACAO_mean": "Redação",
    }

    conn = db_agent._get_conn()
    
    try:
        # 1. Média Nacional (BR)
        sql_br = "SELECT * FROM tb_notas_stats WHERE ANO = ?"
        row_br, cols_br = db_agent.run_query(sql_br, [ano])
        row_br = row_br[0] if row_br else None
        
        # Se não tiver dados nacionais, retorna vazio (ou erro)
        if not row_br:
            return []
                
        dict_br = dict(zip(cols_br, row_br))

        # 2. Média da UF Selecionada
        dict_uf = {}
        if uf:
            sql_uf = "SELECT * FROM tb_notas_geo_uf WHERE ANO = ? AND SG_UF_PROVA = ?"
            row_uf, cols_uf = db_agent.run_query(sql_uf, [ano, uf.upper()])
            row_uf = row_uf[0] if row_uf else None
            if row_uf:
                dict_uf = dict(zip(cols_uf, row_uf))

        # 3. Melhor UF por disciplina (Benchmark)
        # Query otimizada para pegar o MAX de cada coluna
        selects = [f"MAX({k}) as {k}" for k in disciplinas.keys()]
        sql_best = f"SELECT {', '.join(selects)} FROM tb_notas_geo_uf WHERE ANO = ?"
        row_best, cols_best = db_agent.run_query(sql_best, [ano])
        row_best = row_best[0] if row_best else None
        dict_best = dict(zip(cols_best, row_best)) if row_best else {}
        
    except Exception as exc:
        logger.warning(f"Erro ao consultar dados para radar: {exc}")
        return []

    # Montar resposta estruturada
    response = []
    for db_col, label in disciplinas.items():
        response.append({
            "metric": label,
            "br_mean": dict_br.get(db_col),
            "uf_mean": dict_uf.get(db_col),
            "best_uf_mean": dict_best.get(db_col),
            "full_mark": 1000 # Referência visual para o gráfico
        })

    return response
