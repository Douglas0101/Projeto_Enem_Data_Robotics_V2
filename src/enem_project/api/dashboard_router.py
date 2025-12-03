from functools import lru_cache
from typing import List, Annotated
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

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
    municipio: Annotated[str | None, Query(
        description="Nome do Município da prova (NO_MUNICIPIO_PROVA) para filtrar.",
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

    if municipio:
        where_clauses.append("UPPER(NO_MUNICIPIO_PROVA) = ?")
        params.append(municipio.upper())

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
    "/municipios",
    response_model=List[str],
    summary="Lista de municípios disponíveis (para autocomplete).",
)
@lru_cache(maxsize=32)
def get_municipios(
    uf: Annotated[str | None, Query(
        description="Filtrar municípios por UF (opcional).",
        min_length=2,
        max_length=2,
    )] = None
) -> List[str]:
    """
    Retorna a lista de municípios distintos disponíveis no banco de dados.
    Útil para popular combobox/autocomplete no frontend.
    """
    sql = "SELECT DISTINCT NO_MUNICIPIO_PROVA FROM tb_notas_geo"
    params = []
    
    if uf:
        sql += " WHERE SG_UF_PROVA = ?"
        params.append(uf.upper())
        
    sql += " ORDER BY NO_MUNICIPIO_PROVA"

    conn = db_agent._get_conn()
    try:
        rows, columns = db_agent.run_query(sql, params)
    except Exception as exc:
        logger.warning(f"Erro ao listar municípios: {exc}")
        return []

    # Normalização: Title Case e Remove Duplicatas de Casing (ex: "SÃO PAULO" e "São Paulo")
    cities = {row[0].title() for row in rows if row[0]}
    return sorted(list(cities))


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


def _build_geo_query(
    anos: List[int] | None,
    ufs: List[str] | None,
    municipios: List[str] | None,
    min_count: int,
    limit: int | None = None,
    offset: int | None = None,
    is_count_query: bool = False
) -> tuple[str, list[object]]:
    """
    Construtor centralizado de Queries SQL (A "Função Paralela").
    Garante que a tabela visualizada e o arquivo exportado usem EXATAMENTE
    a mesma lógica de filtragem.
    """
    where_clauses: list[str] = []
    params: list[object] = []

    # Filtro de Anos (Lista)
    if anos:
        placeholders = ",".join(["?"] * len(anos))
        where_clauses.append(f"ANO IN ({placeholders})")
        params.extend(anos)

    # Filtro de UFs (Lista)
    if ufs:
        placeholders = ",".join(["?"] * len(ufs))
        # Normaliza para UPPERcase
        clean_ufs = [u.upper() for u in ufs]
        where_clauses.append(f"SG_UF_PROVA IN ({placeholders})")
        params.extend(clean_ufs)

    # Filtro de Municípios (Lista)
    if municipios:
        placeholders = ",".join(["?"] * len(municipios))
        # BLINDAGEM: Normaliza input e coluna para UPPERCASE para garantir match case-insensitive
        clean_municipios = [m.upper() for m in municipios]
        where_clauses.append(f"UPPER(NO_MUNICIPIO_PROVA) IN ({placeholders})")
        params.extend(clean_municipios)

    # Filtro de Amostra Mínima
    if min_count > 0:
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

    if is_count_query:
        sql = f"SELECT COUNT(*) FROM tb_notas_geo {where_sql}"
        return sql, params

    sql = f"""
        SELECT
            ANO,
            SG_UF_PROVA,
            CAST(CO_MUNICIPIO_PROVA AS VARCHAR) AS CO_MUNICIPIO_PROVA,
            NO_MUNICIPIO_PROVA,
            INSCRITOS,
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
        ORDER BY ANO DESC, SG_UF_PROVA, NO_MUNICIPIO_PROVA
    """
    
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset if offset else 0])
        
    return sql, params


@router.get(
    "/notas/geo",
    response_model=List[TbNotasGeoRow],
    summary="Notas agregadas por múltiplos anos/UFs/Municípios.",
)
# @lru_cache removido pois listas não são hashable
def get_notas_geo(
    ano: Annotated[List[int] | None, Query(
        description="Lista de anos. Se omitido, retorna todos.",
    )] = None,
    uf: Annotated[List[str] | None, Query(
        description="Lista de UFs. Se omitido, retorna todas.",
    )] = None,
    municipio: Annotated[List[str] | None, Query(
        description="Lista de nomes de Municípios.",
    )] = None,
    min_count: Annotated[int, Query(
        ge=0,
        description="Filtro mínimo de participantes."
    )] = 30,
    limit: Annotated[int, Query(ge=1, le=100_000)] = 5000,
    page: Annotated[int, Query(ge=1)] = 1,
) -> List[TbNotasGeoRow]:
    """
    Endpoint otimizado com suporte a múltiplos filtros (Listas).
    """
    offset = (page - 1) * limit
    
    # Usa o construtor centralizado com argumentos nomeados (Segurança e Clareza)
    sql, params = _build_geo_query(
        anos=ano, 
        ufs=uf, 
        municipios=municipio, 
        min_count=min_count, 
        limit=limit, 
        offset=offset
    )

    conn = db_agent._get_conn()
    try:
        rows, columns = db_agent.run_query(sql, params)
    except Exception as exc:
        logger.warning(f"Consulta a tb_notas_geo falhou: {exc}")
        return []

    results = []
    for row in rows:
        try:
            data_dict = dict(zip(columns, row))
            # Padronização visual: Força Title Case no Município
            if data_dict.get("NO_MUNICIPIO_PROVA"):
                data_dict["NO_MUNICIPIO_PROVA"] = str(data_dict["NO_MUNICIPIO_PROVA"]).title()
            
            results.append(TbNotasGeoRow(**data_dict))
        except Exception as e:
            continue
    return results


from enem_project.services.report_service import ReportService

@router.get(
    "/notas/geo/export",
    summary="Exportação profissional de dados (Excel, PDF, CSV).",
    response_class=StreamingResponse,
)
def download_notas_geo(
    ano: Annotated[List[int] | None, Query()] = None,
    uf: Annotated[List[str] | None, Query()] = None,
    municipio: Annotated[List[str] | None, Query()] = None,
    min_count: Annotated[int, Query()] = 30,
    format: Annotated[str, Query(regex="^(csv|json|excel|pdf)$")] = "excel"
):
    """
    Gera relatórios profissionais com os MESMOS filtros da tela.
    Suporta:
    - Excel (.xlsx): Formatado com estilos corporativos.
    - PDF: Layout A4 Landscape paginado.
    - CSV: Para interoperabilidade.
    """
    import pandas as pd
    import io
    from fastapi.responses import StreamingResponse

    logger.info(f"--- INICIANDO EXPORTAÇÃO ({format.upper()}) ---")
    logger.info(f"Filtros Recebidos: Anos={ano}, UFs={uf}, Municípios={municipio}, MinCount={min_count}")

    # 1. Busca TODOS os dados filtrados
    sql, params = _build_geo_query(
        anos=ano, 
        ufs=uf, 
        municipios=municipio, 
        min_count=min_count, 
        limit=None, 
        offset=None
    )
    
    logger.debug(f"SQL Gerado: {sql}")
    logger.debug(f"Params SQL: {params}")
    
    try:
        rows, columns = db_agent.run_query(sql, params)
        logger.info(f"Linhas recuperadas do DB: {len(rows)}")
        
        df = pd.DataFrame(rows, columns=columns)
        
        if df.empty:
            logger.warning("DataFrame está VAZIO. O relatório será gerado sem dados.")
        
        # Padronização VISUAL: Converte Municípios para Title Case (ex: PORTO SEGURO -> Porto Seguro)
        if 'NO_MUNICIPIO_PROVA' in df.columns:
            df['NO_MUNICIPIO_PROVA'] = df['NO_MUNICIPIO_PROVA'].astype(str).str.title()

        # Renomear colunas para ficar bonito no relatório
        df.rename(columns={
            'ANO': 'Ano',
            'SG_UF_PROVA': 'Estado',
            'NO_MUNICIPIO_PROVA': 'Município',
            'INSCRITOS': 'Total Inscritos',
            'NOTA_CIENCIAS_NATUREZA_mean': 'Natureza',
            'NOTA_CIENCIAS_HUMANAS_mean': 'Humanas',
            'NOTA_LINGUAGENS_CODIGOS_mean': 'Linguagens',
            'NOTA_MATEMATICA_mean': 'Matemática',
            'NOTA_REDACAO_mean': 'Redação',
            'CO_MUNICIPIO_PROVA': 'Cód. IBGE',
            'NOTA_MATEMATICA_count': 'Qtd. Provas'
        }, inplace=True)

        # Garantir que 'Qtd. Provas' seja inteiro
        if 'Qtd. Provas' in df.columns:
            df['Qtd. Provas'] = df['Qtd. Provas'].fillna(0).astype(int)
        
        if 'Total Inscritos' in df.columns:
            df['Total Inscritos'] = df['Total Inscritos'].fillna(0).astype(int)
        
        # Selecionar colunas relevantes para o relatório (remove contagens internas exceto a principal)
        cols_to_show = [
            'Ano', 'Estado', 'Município', 'Total Inscritos', 'Natureza', 'Humanas', 
            'Linguagens', 'Matemática', 'Redação', 'Qtd. Provas'
        ]
        # Garante que só mostra colunas que existem (caso a query mude)
        final_cols = [c for c in cols_to_show if c in df.columns]
        df_report = df[final_cols]

        if format == 'excel':
            # Gera binário XLSX via ReportService
            file_content = ReportService.generate_excel(df_report)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"enem_relatorio_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
        elif format == 'pdf':
            # Formatação limpa: Remove colchetes e parênteses técnicos
            if ano:
                anos_texto = ", ".join(str(a) for a in sorted(ano))
            else:
                anos_texto = "Todos os Anos Disponíveis"

            # Formatação limpa de UFs: ["BA", "SP"] -> "BA, SP"
            ufs_texto = "Todas as UFs"
            if uf:
                ufs_texto = ", ".join(sorted(uf))
            
            # Formatação limpa de Municípios: ["Porto Seguro"] -> "Porto Seguro"
            municipios_texto = "Todos os Municípios"
            if municipio:
                # Resumo se muitos municípios
                if len(municipio) > 3:
                    municipios_texto = f"{', '.join(sorted(municipio[:3]))} e mais {len(municipio) - 3}"
                else:
                    municipios_texto = ", ".join(sorted(municipio))

            # Gera binário PDF via ReportService com título profissional
            file_content = ReportService.generate_pdf(
                df_report, 
                title=f"Relatório de Desempenho Municipal ENEM",
                filter_summary=f"Anos: {anos_texto} | UFs: {ufs_texto} | Municípios: {municipios_texto}"
            )
            media_type = "application/pdf"
            filename = f"enem_relatorio_{datetime.now().strftime('%Y%m%d')}.pdf"
            
        elif format == 'json':
            stream = io.StringIO()
            df_report.to_json(stream, orient="records", force_ascii=False)
            file_content = stream.getvalue().encode('utf-8')
            media_type = "application/json"
            filename = "dados_enem.json"
            
        else: # CSV
            stream = io.StringIO()
            df_report.to_csv(stream, index=False, sep=';', decimal=',', encoding='utf-8-sig')
            file_content = stream.getvalue().encode('utf-8-sig')
            media_type = "text/csv"
            filename = "dados_enem.csv"

        # Retorna o Stream
        return StreamingResponse(
            io.BytesIO(file_content), 
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as exc:
        logger.error(f"Erro na exportação ({format}): {exc}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(exc)}")


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