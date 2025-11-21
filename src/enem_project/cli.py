from __future__ import annotations

from typing import Optional, List
import sys
import subprocess
import typer

from enem_project.config.settings import settings
from enem_project.data.silver_to_gold import (
    build_tb_notas_parquet_streaming,
    build_tb_notas_geo_from_cleaned,
    build_tb_notas_stats_from_cleaned,
)
from enem_project.orchestrator.workflows.audit_workflow import run_quality_audit_for_years
from enem_project.orchestrator.workflows.class_workflow import run_class_workflow
from enem_project.orchestrator.workflows.etl_workflow import run_etl_full
from enem_project.orchestrator.workflows.sql_backend_workflow import init_sql_backend
from enem_project.infra.logging import logger


def _main(
    ano: Optional[int] = typer.Option(
        None,
        "--ano",
        "-a",
        help=(
            "Ano específico para processar (ex.: 2022). "
            "Se não for informado, roda para todos os anos configurados."
        ),
    ),
    ano_inicio: Optional[int] = typer.Option(
        None,
        "--ano-inicio",
        help="Ano inicial do intervalo a processar (inclusive).",
    ),
    ano_fim: Optional[int] = typer.Option(
        None,
        "--ano-fim",
        help="Ano final do intervalo a processar (inclusive).",
    ),
    anos: Optional[List[int]] = typer.Option(
        None,
        "--anos",
        help=(
            "Lista explícita de anos para processar, "
            "por exemplo: --anos 1998 1999 2000."
        ),
    ),
    auditoria: bool = typer.Option(
        False,
        "--auditoria",
        help=(
            "Executa somente a auditoria de qualidade dos Parquets (linhas/colunas), "
            "sem reprocessar o ETL."
        ),
    ),
    classe: bool = typer.Option(
        False,
        "--classe",
        help=(
            "Executa somente o workflow avançado de limpeza e engenharia de classes, "
            "gerando tabelas na camada gold."
        ),
    ),
    sql_backend: bool = typer.Option(
        False,
        "--sql-backend",
        help=(
            "Inicializa o backend SQL (DuckDB) para consumo via SQL, "
            "materializando tabelas tb_notas, tb_notas_stats e tb_notas_geo."
        ),
    ),
) -> None:
    """
    Roda o workflow ETL completo (RAW → SILVER + QA) para um ou mais anos.
    """
    if anos:
        anos_alvo = sorted(set(int(a) for a in anos))
    elif ano is not None:
        anos_alvo = [int(ano)]
    elif ano_inicio is not None or ano_fim is not None:
        ini = ano_inicio if ano_inicio is not None else min(settings.years)
        fim = ano_fim if ano_fim is not None else max(settings.years)
        anos_alvo = [y for y in settings.years if ini <= y <= fim]
    else:
        # Comportamento legado: todos os anos configurados em settings.years
        anos_alvo = list(settings.years)

    if sum(bool(flag) for flag in (auditoria, classe, sql_backend)) > 1:
        raise typer.BadParameter(
            "Use apenas um modo especial por vez "
            "(--auditoria, --classe ou --sql-backend).",
        )

    if sql_backend:
        db_path = init_sql_backend(materialize_dashboard_tables=True)
        logger.info(
            "Backend SQL inicializado em %s (DuckDB). "
            "Tabelas tb_notas, tb_notas_stats e tb_notas_geo disponíveis para consumo.",
            db_path,
        )
        typer.echo(
            f"✅ Backend SQL (DuckDB) inicializado em: {db_path}"
        )
        return

    if auditoria:
        audit_result = run_quality_audit_for_years(anos_alvo)
        logger.info(
            "Auditoria concluída para anos: %s | Relatório: %s",
            anos_alvo,
            audit_result["report_path"],
        )
        typer.echo(
            f"✅ Auditoria concluída para anos: {anos_alvo} "
            f"(relatório: {audit_result['report_path']})"
        )
        return

    if classe:
        results = run_class_workflow(anos_alvo)
        anos_processados = sorted(results.keys())
        logger.info(
            "Workflow de classes finalizado para anos: %s | tabelas em data/02_gold/classes",
            anos_processados,
        )
        # Após limpeza + classes, gera também as tabelas de notas
        # consolidadas usadas pelos dashboards descritivos/estatísticos.
        tb_notas_rows = build_tb_notas_parquet_streaming(anos_alvo)
        stats_df = build_tb_notas_stats_from_cleaned(anos_alvo)
        geo_df = build_tb_notas_geo_from_cleaned(anos_alvo)
        logger.info(
            "Tabelas de notas para dashboard atualizadas em data/02_gold "
            "(tb_notas, tb_notas_stats, tb_notas_geo) | linhas tb_notas=%d, "
            "tb_notas_stats=%d, tb_notas_geo=%d",
            tb_notas_rows,
            len(stats_df),
            len(geo_df),
        )
        typer.echo(
            f"✅ Limpeza, engenharia de classes e tabelas de notas para dashboard "
            f"concluídas para anos: {anos_processados}"
        )
        return

    if len(anos_alvo) == 1:
        # Mantém compatibilidade com logs/uso de run_etl_full para um único ano
        results = run_etl_full(anos_alvo[0])
        anos_processados = sorted(results.keys())
        logger.info(f"Workflows ETL finalizados para anos: {anos_processados}")
        typer.echo(f"✅ ETL concluído para anos: {anos_processados}")
        return

    # Para múltiplos anos, rodamos cada ano em um processo separado
    # para evitar acumular uso de memória em execuções muito longas.
    anos_processados: list[int] = []
    for target_year in anos_alvo:
        typer.echo(f"▶ Rodando ETL isolado para ano {target_year}...")
        code = subprocess.call(
            [sys.executable, "-m", "enem_project.cli", "--ano", str(target_year)],
        )
        if code != 0:
            raise typer.Exit(code)
        anos_processados.append(int(target_year))

    anos_processados = sorted(set(anos_processados))
    logger.info(f"Workflows ETL finalizados para anos (multi-processo): {anos_processados}")
    typer.echo(f"✅ ETL concluído para anos: {anos_processados}")


def main() -> None:
    """
    Entry-point chamado pelo console script `enem`.
    """
    typer.run(_main)


if __name__ == "__main__":
    main()
