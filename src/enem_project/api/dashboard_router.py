from typing import List, Annotated, Any
from datetime import datetime
import io
import pandas as pd

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool

from ..infra.db_agent import DuckDBAgent
from ..infra.logging import logger
from ..infra.security import SecurityEngine
from ..services.report_service import ReportService
from .schemas import (
    TbNotasGeoRow,
    TbNotasStatsRow,
    TbNotasGeoUfRow,
    TbNotasHistogramRow,
    TbSocioRaceRow,
    TbSocioIncomeRow,
    TbRadarRow,
)
from .dependencies import get_db_agent
from .limiter import limiter


router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])

# Normalização para comparações acento/case-insensitive de municípios
ACCENT_FROM = "ÁÀÂÃÄáàâãäÉÈÊËéèêëÍÌÎÏíìîïÓÒÔÕÖóòôõöÚÙÛÜúùûüÇç"
ACCENT_TO = "AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuCc"
ACCENT_TRANSLATION = str.maketrans(ACCENT_FROM, ACCENT_TO)
MUNICIPIO_SQL_NORMALIZED = (
    f"translate(upper(NO_MUNICIPIO_PROVA), '{ACCENT_FROM}', '{ACCENT_TO}')"
)


def _normalize_text(value: str | None) -> str:
    """Remove acentos e aplica upper/trim para comparação estável."""
    if not value:
        return ""
    return value.translate(ACCENT_TRANSLATION).upper().strip()


@router.get(
    "/advanced/socioeconomic/race",
    response_model=List[TbSocioRaceRow],
    summary="Médias de notas por Cor/Raça (Real Data).",
)
@limiter.limit("60/minute")
async def get_socioeconomic_race(
    request: Request,
    agent: Annotated[DuckDBAgent, Depends(get_db_agent)],
    ano: Annotated[int | None, Query(description="Ano de referência.")] = None,
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    municipio: Annotated[str | None, Query()] = None,
) -> List[TbSocioRaceRow]:
    """
    Retorna a média das notas agrupadas por autodeclaração de cor/raça.
    """
    where_clauses: list[str] = []
    params: list[Any] = []

    if ano is not None:
        where_clauses.append("ANO = ?")
        params.append(ano)

    if uf:
        where_clauses.append("SG_UF_PROVA = ?")
        params.append(uf.upper())

    if municipio:
        where_clauses.append(f"{MUNICIPIO_SQL_NORMALIZED} = ?")
        params.append(_normalize_text(municipio))

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Conditional Grouping
    group_cols = ["TP_COR_RACA"]
    select_ano = "NULL as ANO"

    if ano is None:
        group_cols.insert(0, "ANO")
        select_ano = "ANO"

    group_sql = ", ".join(group_cols)

    sql = f"""
        SELECT 
            {select_ano},
            TP_COR_RACA,
            AVG(NOTA_MATEMATICA) as NOTA_MATEMATICA,
            AVG(NOTA_CIENCIAS_NATUREZA) as NOTA_CIENCIAS_NATUREZA,
            AVG(NOTA_CIENCIAS_HUMANAS) as NOTA_CIENCIAS_HUMANAS,
            AVG(NOTA_LINGUAGENS_CODIGOS) as NOTA_LINGUAGENS_CODIGOS,
            AVG(NOTA_REDACAO) as NOTA_REDACAO,
            COUNT(*) as COUNT
        FROM gold_classes
        {where_sql}
        GROUP BY {group_sql}
        HAVING COUNT(*) > 100
        ORDER BY ANO DESC, COUNT DESC
    """  # nosec B608

    race_map = {
        0: "Não Declarado",
        1: "Branca",
        2: "Preta",
        3: "Parda",
        4: "Amarela",
        5: "Indígena",
        6: "Não Disp.",
    }

    try:
        rows, columns = await run_in_threadpool(agent.run_query, sql, params)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar dados socioeconômicos: {exc}",
        ) from exc

    result = []
    for row in rows:
        ano_val = row[0]
        tp_raca = row[1]
        if tp_raca is None:
            label = race_map[6]
        else:
            label = race_map.get(tp_raca, f"Outros ({tp_raca})")

        result.append(
            TbSocioRaceRow(
                ANO=ano_val,
                RACA=label,
                NOTA_MATEMATICA=row[2],
                NOTA_CIENCIAS_NATUREZA=row[3],
                NOTA_CIENCIAS_HUMANAS=row[4],
                NOTA_LINGUAGENS_CODIGOS=row[5],
                NOTA_REDACAO=row[6],
                COUNT=row[7],
            )
        )

    return result


@router.get(
    "/advanced/socioeconomic/income",
    response_model=List[TbSocioIncomeRow],
    summary="Distribuição de Notas por Renda.",
)
@limiter.limit("60/minute")
async def get_socioeconomic_income(
    request: Request,
    agent: Annotated[DuckDBAgent, Depends(get_db_agent)],
    ano: Annotated[int, Query(description="Ano de referência.")],
) -> List[TbSocioIncomeRow]:
    sql = """
        SELECT CLASSE, LOW, Q1, MEDIAN, Q3, HIGH
        FROM tb_socio_economico
        WHERE ANO = ?
        ORDER BY CLASSE
    """

    try:
        rows, columns = await run_in_threadpool(agent.run_query, sql, [ano])
    except Exception as exc:
        logger.error(f"Erro ao ler tb_socio_economico: {exc}")
        # Don't return empty list silently on DB error unless it's an expected "table missing" scenario
        if "does not exist" in str(exc):
            return []
        raise HTTPException(
            status_code=500, detail="Database error processing income stats."
        )

    return [
        TbSocioIncomeRow(
            CLASSE=row[0], LOW=row[1], Q1=row[2], MEDIAN=row[3], Q3=row[4], HIGH=row[5]
        )
        for row in rows
    ]


@router.get(
    "/municipios",
    response_model=List[str],
    summary="Lista de municípios disponíveis.",
)
@limiter.limit("100/minute")
async def get_municipios(
    request: Request,
    agent: Annotated[DuckDBAgent, Depends(get_db_agent)],
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
) -> List[str]:
    sql = "SELECT DISTINCT NO_MUNICIPIO_PROVA FROM tb_notas_geo"
    params = []

    if uf:
        sql += " WHERE SG_UF_PROVA = ?"
        params.append(uf.upper())

    sql += " ORDER BY NO_MUNICIPIO_PROVA"

    try:
        rows, columns = await run_in_threadpool(agent.run_query, sql, params)
    except Exception as exc:
        logger.error(f"Erro ao listar municípios: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch municipalities")

    norm_to_city: dict[str, str] = {}
    for row in rows:
        raw_city = row[0]
        if not raw_city:
            continue
        display = raw_city.title()
        norm_key = _normalize_text(display)
        current = norm_to_city.get(norm_key)
        if current is None or (current.isascii() and not display.isascii()):
            norm_to_city[norm_key] = display

    return sorted(norm_to_city.values())


@router.get(
    "/anos-disponiveis",
    response_model=List[int],
    summary="Lista de anos disponíveis.",
)
@limiter.limit("100/minute")
async def get_anos_disponiveis(
    request: Request, agent: Annotated[DuckDBAgent, Depends(get_db_agent)]
) -> List[int]:
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

    try:
        rows, columns = await run_in_threadpool(agent.run_query, sql)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar anos disponíveis: {exc}",
        ) from exc

    return [int(row[0]) for row in rows]


@router.get(
    "/notas/stats",
    response_model=List[TbNotasStatsRow],
    summary="Estatísticas anuais de notas.",
)
@limiter.limit("100/minute")
async def get_notas_stats(
    request: Request,
    agent: Annotated[DuckDBAgent, Depends(get_db_agent)],
    ano_inicio: Annotated[int | None, Query()] = None,
    ano_fim: Annotated[int | None, Query()] = None,
) -> List[TbNotasStatsRow]:
    where_clauses: list[str] = []
    params: list[Any] = []

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
    """  # nosec B608

    try:
        rows, columns = await run_in_threadpool(agent.run_query, sql, params)
    except Exception as exc:
        logger.error(f"Query error in get_notas_stats: {exc}")
        if "does not exist" in str(exc):
            return []
        raise HTTPException(status_code=500, detail="Database error.")

    results = []
    for row in rows:
        try:
            results.append(TbNotasStatsRow(**dict(zip(columns, row))))
        except Exception as e:
            logger.warning(f"Invalid data in row, skipping: {e}")
            continue

    return results


def _build_geo_query(
    anos: List[int] | None,
    ufs: List[str] | None,
    municipios: List[str] | None,
    min_count: int,
    limit: int | None = None,
    offset: int | None = None,
    is_count_query: bool = False,
) -> tuple[str, list[Any]]:
    where_clauses: list[str] = []
    params: list[Any] = []

    if anos:
        placeholders = ",".join(["?" for _ in anos])
        where_clauses.append(f"ANO IN ({placeholders})")
        params.extend(anos)

    if ufs:
        placeholders = ",".join(["?" for _ in ufs])
        clean_ufs = [u.upper() for u in ufs]
        where_clauses.append(f"SG_UF_PROVA IN ({placeholders})")
        params.extend(clean_ufs)

    if municipios:
        placeholders = ",".join(["?" for _ in municipios])
        clean_municipios = [_normalize_text(m) for m in municipios]
        where_clauses.append(f"{MUNICIPIO_SQL_NORMALIZED} IN ({placeholders})")
        params.extend(clean_municipios)

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
        sql = f"SELECT COUNT(*) FROM tb_notas_geo {where_sql}"  # nosec B608
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
    """  # nosec B608

    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset if offset else 0])

    return sql, params


@router.get(
    "/notas/geo",
    response_model=List[TbNotasGeoRow],
    summary="Notas agregadas por múltiplos anos/UFs/Municípios.",
)
@limiter.limit("60/minute")
async def get_notas_geo(
    request: Request,
    agent: Annotated[DuckDBAgent, Depends(get_db_agent)],
    ano: Annotated[List[int] | None, Query()] = None,
    uf: Annotated[List[str] | None, Query()] = None,
    municipio: Annotated[List[str] | None, Query()] = None,
    min_count: Annotated[int, Query(ge=0)] = 30,
    limit: Annotated[int, Query(ge=1, le=100_000)] = 5000,
    page: Annotated[int, Query(ge=1)] = 1,
) -> List[TbNotasGeoRow]:
    offset = (page - 1) * limit
    sql, params = _build_geo_query(
        anos=ano,
        ufs=uf,
        municipios=municipio,
        min_count=min_count,
        limit=limit,
        offset=offset,
    )

    try:
        rows, columns = await run_in_threadpool(agent.run_query, sql, params)
    except Exception as exc:
        logger.warning(f"Consulta a tb_notas_geo falhou: {exc}")
        raise HTTPException(status_code=500, detail="Database Query Failed")

    results = []
    for row in rows:
        try:
            data_dict = dict(zip(columns, row))
            if data_dict.get("NO_MUNICIPIO_PROVA"):
                data_dict["NO_MUNICIPIO_PROVA"] = str(
                    data_dict["NO_MUNICIPIO_PROVA"]
                ).title()
            results.append(TbNotasGeoRow(**data_dict))
        except Exception:
            continue  # nosec B112
    return results


@router.get(
    "/notas/geo/export",
    summary="Exportação profissional de dados (Excel, PDF, CSV) com Streaming.",
    response_class=StreamingResponse,
)
@limiter.limit("5/hour")
async def download_notas_geo(
    request: Request,
    agent: Annotated[DuckDBAgent, Depends(get_db_agent)],
    ano: Annotated[List[int] | None, Query()] = None,
    uf: Annotated[List[str] | None, Query()] = None,
    municipio: Annotated[List[str] | None, Query()] = None,
    min_count: Annotated[int, Query()] = 30,
    format: Annotated[str, Query(pattern="^(csv|json|excel|pdf)$")] = "excel",
):
    """
    Endpoint de exportação refatorado para Memory Safety e Non-blocking I/O.
    """
    logger.info(f"--- INICIANDO EXPORTAÇÃO ({format.upper()}) ---")

    # Builds SQL without LIMIT/OFFSET for export
    sql, params = _build_geo_query(
        anos=ano,
        ufs=uf,
        municipios=municipio,
        min_count=min_count,
        limit=None,
        offset=None,
    )

    # Guardrail: Check row count before loading heavy formats
    count_sql = f"SELECT COUNT(*) FROM ({sql})"  # nosec B608

    try:
        # Using run_in_threadpool for the count query to keep event loop free
        count_res, _ = await run_in_threadpool(agent.run_query, count_sql, params)
        total_rows = count_res[0][0]

        # Limit for in-memory generation formats (Excel/PDF)
        MEMORY_LIMIT = 50000

        if format in ("excel", "pdf") and total_rows > MEMORY_LIMIT:
            raise HTTPException(
                status_code=400,
                detail=f"Exportação para {format.upper()} excedeu o limite de {MEMORY_LIMIT} linhas ({total_rows}). Por favor, filtre mais os dados ou use CSV.",
            )

        # --- STREAMING GENERATORS ---

        async def iter_csv():
            """Streams CSV rows directly from DB cursor without loading all to memory."""
            conn = agent.get_connection()  # Access connection safely
            cursor = conn.cursor()
            cursor.execute(sql, params)

            # Yield Header
            columns = [col[0] for col in cursor.description]
            yield ";".join(columns) + "\n"

            # Stream chunks
            while True:
                # Fetch in chunks to keep memory low
                chunk = await run_in_threadpool(cursor.fetchmany, 5000)
                if not chunk:
                    break
                for row in chunk:
                    # Basic CSV formatting
                    cleaned_row = [
                        str(val).replace(";", ",") if val is not None else ""
                        for val in row
                    ]
                    yield ";".join(cleaned_row) + "\n"

            cursor.close()

        async def iter_json():
            """Streams JSON lines."""
            import json

            conn = agent.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]

            yield "["
            first = True
            while True:
                chunk = await run_in_threadpool(cursor.fetchmany, 5000)
                if not chunk:
                    break
                for row in chunk:
                    if not first:
                        yield ","
                    else:
                        first = False

                    data = dict(zip(columns, row))
                    yield json.dumps(data, ensure_ascii=False)
            yield "]"
            cursor.close()

        # --- RESPONSE DISPATCH ---

        if format == "csv":
            return StreamingResponse(
                iter_csv(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=dados_enem_{datetime.now().strftime('%Y%m%d')}.csv"
                },
            )

        elif format == "json":
            return StreamingResponse(
                iter_json(),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=dados_enem.json"},
            )

        elif format in ("excel", "pdf"):
            # For Excel/PDF, we sadly still need to load into DataFrame for the libraries to work.
            # But we are protected by MEMORY_LIMIT check above and run in threadpool.
            def generate_binary():
                rows, columns = agent.run_query(sql, params, row_limit=MEMORY_LIMIT + 1)
                df = pd.DataFrame(rows, columns=columns)

                # Pre-processing
                if "NO_MUNICIPIO_PROVA" in df.columns:
                    df["NO_MUNICIPIO_PROVA"] = (
                        df["NO_MUNICIPIO_PROVA"].astype(str).str.title()
                    )

                # --- SECURITY: DYNAMIC MASKING ---
                # Apply LGPD protection for non-admin users.
                # Since we don't have AUTH yet, we default to 'user' (safe by default).
                # In future, extract role from request.user.role
                df = SecurityEngine.apply_dynamic_masking(df, role="user")

                # Mapa completo de renomeação para evitar colunas "cruas" no relatório
                rename_map = {
                    "ANO": "Ano",
                    "SG_UF_PROVA": "UF",
                    "NO_MUNICIPIO_PROVA": "Município",
                    "CO_MUNICIPIO_PROVA": "Cód. IBGE",
                    "INSCRITOS": "Inscritos",
                    # Vamos usar NOTA_REDACAO_count como proxy de "Qtd. Provas" (presentes no dia 1)
                    # e remover os outros counts duplicados.
                    "NOTA_REDACAO_count": "Provas Aplicadas",
                    # Médias das 5 Disciplinas - Nomes por extenso conforme solicitado
                    "NOTA_CIENCIAS_NATUREZA_mean": "Ciências da Natureza",
                    "NOTA_CIENCIAS_HUMANAS_mean": "Ciências Humanas",
                    "NOTA_LINGUAGENS_CODIGOS_mean": "Linguagens e Códigos",
                    "NOTA_MATEMATICA_mean": "Matemática",
                    "NOTA_REDACAO_mean": "Redação",
                }

                # Rename cols
                df.rename(columns=rename_map, inplace=True)

                # Filtra colunas para manter apenas o solicitado:
                # "são cinco disciplinas, quantidade de inscritos e provas, somente isso"
                # + Identificadores (Ano, UF, Município)
                cols_to_keep = [
                    "Ano",
                    "UF",
                    "Município",
                    "Inscritos",
                    "Provas Aplicadas",
                    "Ciências da Natureza",
                    "Ciências Humanas",
                    "Linguagens e Códigos",
                    "Matemática",
                    "Redação",
                ]

                # Mantém apenas as colunas desejadas que existem no DF
                final_cols = [c for c in cols_to_keep if c in df.columns]
                df = df[final_cols]

                # Construção do texto de filtro dinâmico
                filter_parts = []
                if ano:
                    filter_parts.append(f"Anos: {', '.join(map(str, sorted(ano)))}")
                if uf:
                    filter_parts.append(f"UFs: {', '.join(sorted(uf))}")
                if municipio:
                    m_str = ", ".join(sorted(municipio))
                    if len(m_str) > 60:
                        m_str = m_str[:57] + "..."
                    filter_parts.append(f"Municípios: {m_str}")

                filter_text = (
                    " | ".join(filter_parts)
                    if filter_parts
                    else "Filtros: Todos os registros"
                )

                if format == "excel":
                    return (
                        ReportService.generate_excel(df),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "xlsx",
                    )
                else:
                    return (
                        ReportService.generate_pdf(
                            df,
                            title="Relatório de Desempenho",
                            filter_summary=filter_text,
                        ),
                        "application/pdf",
                        "pdf",
                    )

            # Execute heavy generation in threadpool
            file_content, media_type, ext = await run_in_threadpool(generate_binary)

            return StreamingResponse(
                io.BytesIO(file_content),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename=enem_relatorio_{datetime.now().strftime('%Y%m%d')}.{ext}"
                },
            )

    except HTTPException as he:
        raise he
    except Exception as exc:
        logger.error(f"Export error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to export data.")


@router.get(
    "/notas/geo-uf",
    response_model=List[TbNotasGeoUfRow],
    summary="Notas agregadas por ano/UF.",
)
@limiter.limit("60/minute")
async def get_notas_geo_uf(
    request: Request,
    agent: Annotated[DuckDBAgent, Depends(get_db_agent)],
    ano: Annotated[int | None, Query()] = None,
    min_inscritos: Annotated[int, Query()] = 100,
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
) -> List[TbNotasGeoUfRow]:
    where_clauses: list[str] = ["INSCRITOS >= ?"]
    params: list[Any] = [min_inscritos]

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
    """  # nosec B608

    try:
        rows, columns = await run_in_threadpool(agent.run_query, sql, params)
    except Exception as exc:
        if "does not exist" in str(exc):
            return []
        logger.warning(f"Query fail: {exc}")
        raise HTTPException(status_code=500, detail="Database query error.")

    required_fields = list(TbNotasGeoUfRow.model_fields.keys())
    results = []

    for row in rows:
        try:
            record = dict(zip(columns, row))
            # Data hygiene
            for field in required_fields:
                if field not in record:
                    record[field] = None
            results.append(TbNotasGeoUfRow(**record))
        except Exception:
            continue  # nosec B112
    return results


@router.get(
    "/notas/histograma",
    response_model=List[TbNotasHistogramRow],
    summary="Dados para histograma de notas.",
)
@limiter.limit("60/minute")
async def get_notas_histograma(
    request: Request,
    agent: Annotated[DuckDBAgent, Depends(get_db_agent)],
    ano: Annotated[int, Query()],
    disciplina: Annotated[str, Query()],
) -> List[TbNotasHistogramRow]:
    sql = """
        SELECT ANO, DISCIPLINA, BIN_START, BIN_END, CONTAGEM
        FROM tb_notas_histogram
        WHERE ANO = ? AND DISCIPLINA = ?
        ORDER BY BIN_START
    """
    try:
        rows, columns = await run_in_threadpool(agent.run_query, sql, [ano, disciplina])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB Error: {exc}")

    return [TbNotasHistogramRow(**dict(zip(columns, row))) for row in rows]


@router.get(
    "/advanced/radar",
    response_model=List[TbRadarRow],
    summary="Dados para radar comparativo.",
)
@limiter.limit("60/minute")
async def get_radar_data(
    request: Request,
    agent: Annotated[DuckDBAgent, Depends(get_db_agent)],
    ano: Annotated[int, Query()],
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
) -> List[TbRadarRow]:
    disciplinas = {
        "NOTA_MATEMATICA_mean": "Matemática",
        "NOTA_CIENCIAS_NATUREZA_mean": "Ciências da Natureza",
        "NOTA_CIENCIAS_HUMANAS_mean": "Ciências Humanas",
        "NOTA_LINGUAGENS_CODIGOS_mean": "Linguagens e Códigos",
        "NOTA_REDACAO_mean": "Redação",
    }

    try:
        # run_in_threadpool used for multiple sequential queries
        def fetch_radar():
            # 1. BR Mean
            row_br, cols_br = agent.run_query(
                "SELECT * FROM tb_notas_stats WHERE ANO = ?", [ano]
            )
            row_br = row_br[0] if row_br else None
            dict_br = dict(zip(cols_br, row_br)) if row_br else {}

            # 2. UF Mean
            dict_uf = {}
            if uf:
                row_uf, cols_uf = agent.run_query(
                    "SELECT * FROM tb_notas_geo_uf WHERE ANO = ? AND SG_UF_PROVA = ?",
                    [ano, uf.upper()],
                )
                row_uf = row_uf[0] if row_uf else None
                if row_uf:
                    dict_uf = dict(zip(cols_uf, row_uf))

            # 3. Best UF
            selects = [f"MAX({k}) as {k}" for k in disciplinas.keys()]
            sql_best = f"SELECT {', '.join(selects)} FROM tb_notas_geo_uf WHERE ANO = ?"  # nosec B608
            row_best, cols_best = agent.run_query(sql_best, [ano])
            row_best = row_best[0] if row_best else None
            dict_best = dict(zip(cols_best, row_best)) if row_best else {}

            return dict_br, dict_uf, dict_best

        dict_br, dict_uf, dict_best = await run_in_threadpool(fetch_radar)

        if not dict_br:
            return []

    except Exception as exc:
        logger.error(f"Radar query failed: {exc}")
        raise HTTPException(
            status_code=500, detail="Error processing radar chart data."
        )

    response = []
    for db_col, label in disciplinas.items():
        response.append(
            TbRadarRow(
                metric=label,
                br_mean=dict_br.get(db_col),
                uf_mean=dict_uf.get(db_col),
                best_uf_mean=dict_best.get(db_col),
                full_mark=1000,
            )
        )

    return response
