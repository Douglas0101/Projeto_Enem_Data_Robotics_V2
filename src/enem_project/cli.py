from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List
import sys
import subprocess
import typer

from enem_project.config.settings import settings
from enem_project.data.silver_to_gold import (
    build_tb_notas_parquet_streaming,
    build_tb_notas_geo_from_cleaned,
    build_tb_notas_stats_from_cleaned,
    build_tb_notas_geo_uf_from_cleaned,
)
from enem_project.orchestrator.workflows.audit_workflow import run_quality_audit_for_years
from enem_project.orchestrator.workflows.class_workflow import run_class_workflow
from enem_project.orchestrator.workflows.etl_workflow import run_etl_full
from enem_project.orchestrator.workflows.sql_backend_workflow import run_sql_backend_workflow
from enem_project.infra.logging import logger
from enem_project.orchestrator.mcp_docs import (
    Context7DocsClient,
    MCPConfigError,
    MCPRemoteError,
)


app = typer.Typer(add_completion=False, no_args_is_help=False)


def _run_default(
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
    dashboard: bool = typer.Option(
        False,
        "--dashboard",
        help=(
            "Pipeline unificado para consumo de dashboard: roda limpeza + classes, "
            "gera tb_notas*, materializa DuckDB e aplica quality gate."
        ),
    ),
    skip_existing: bool = typer.Option(
        False,
        "--skip-existing",
        help=(
            "Quando usado com --dashboard, pula anos que já possuem cleaned "
            "em data/02_gold/cleaned para evitar reprocessamento desnecessário."
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

    if sum(bool(flag) for flag in (auditoria, classe, sql_backend, dashboard)) > 1:
        raise typer.BadParameter(
            "Use apenas um modo especial por vez "
            "(--auditoria, --classe, --dashboard ou --sql-backend).",
        )

    if sql_backend:
        db_path = run_sql_backend_workflow(materialize_dashboard_tables=True)
        logger.info(
            "Backend SQL inicializado em %s (DuckDB). "
            "Tabelas tb_notas, tb_notas_stats e tb_notas_geo disponíveis para consumo.",
            db_path,
        )
        typer.echo(
            f"✅ Backend SQL (DuckDB) inicializado em: {db_path}"
        )
        return

    if dashboard:
        anos_exec = list(anos_alvo)
        if skip_existing:
            from enem_project.config.paths import gold_dir

            def _cleaned_exists(y: int) -> bool:
                return (gold_dir() / "cleaned" / f"microdados_enem_{y}_clean.parquet").exists()

            anos_exec = [y for y in anos_alvo if not _cleaned_exists(y)]
            if not anos_exec:
                typer.echo("✅ Nenhum ano a processar (cleaned já existente). Materializando DuckDB...")
                db_path = run_sql_backend_workflow(materialize_dashboard_tables=True)
                typer.echo(f"✅ Backend SQL (DuckDB) materializado em: {db_path}")
                return

        results = run_class_workflow(anos_exec)
        anos_processados = sorted(results.keys())
        logger.info(
            "[dashboard] Limpeza + classes concluídas para anos: %s",
            anos_processados,
        )
        tb_notas_rows = build_tb_notas_parquet_streaming(anos_exec)
        stats_df = build_tb_notas_stats_from_cleaned(anos_exec)
        geo_df = build_tb_notas_geo_from_cleaned(anos_exec)
        geo_uf_df = build_tb_notas_geo_uf_from_cleaned(anos_exec)
        db_path = run_sql_backend_workflow(materialize_dashboard_tables=True)
        logger.info(
            "[dashboard] Tabelas de notas atualizadas (tb_notas=%d, stats=%d, geo=%d, geo_uf=%d) "
            "e backend SQL materializado em %s.",
            tb_notas_rows,
            len(stats_df),
            len(geo_df),
            len(geo_uf_df),
            db_path,
        )
        typer.echo(
            "✅ Dashboard pronto: limpeza+classes, tabelas tb_notas*, backend SQL "
            f"materializado em {db_path} | anos processados: {anos_exec}"
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
        geo_uf_df = build_tb_notas_geo_uf_from_cleaned(anos_alvo)
        logger.info(
            "Tabelas de notas para dashboard atualizadas em data/02_gold "
            "(tb_notas, tb_notas_stats, tb_notas_geo, tb_notas_geo_uf) | linhas tb_notas=%d, "
            "tb_notas_stats=%d, tb_notas_geo=%d, tb_notas_geo_uf=%d",
            tb_notas_rows,
            len(stats_df),
            len(geo_df),
            len(geo_uf_df),
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


@app.callback(invoke_without_command=True)
def cli_entrypoint(
    ctx: typer.Context,
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
    dashboard: bool = typer.Option(
        False,
        "--dashboard",
        help=(
            "Pipeline unificado para consumo de dashboard: roda limpeza + classes, "
            "gera tb_notas*, materializa DuckDB e aplica quality gate."
        ),
    ),
    skip_existing: bool = typer.Option(
        False,
        "--skip-existing",
        help=(
            "Quando usado com --dashboard, pula anos que já possuem cleaned "
            "em data/02_gold/cleaned para evitar reprocessamento desnecessário."
        ),
    ),
    ) -> None:
    """
    Entry-point chamado pelo console script `enem`.
    """
    if ctx.invoked_subcommand:
        return
    _run_default(
        ano=ano,
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
        anos=anos,
        auditoria=auditoria,
        classe=classe,
        sql_backend=sql_backend,
        dashboard=dashboard,
        skip_existing=skip_existing,
    )


@app.command("mcp-docs")
def mcp_docs(
    resource: str = typer.Option(
        ...,
        "--resource",
        "-r",
        help="Resource ID oficial (ex.: /python/documentation).",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Consulta ou filtro de snippets.",
    ),
    max_snippets: int = typer.Option(
        5,
        "--max-snippets",
        help="Limite de snippets retornados pelo MCP.",
    ),
    allow_unlisted: bool = typer.Option(
        False,
        "--allow-unlisted",
        help="Permite recursos fora da whitelist local.",
    ),
    refresh_remote: bool = typer.Option(
        False,
        "--refresh-remote",
        help="Força refresh da lista de recursos remotos antes da consulta.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Nao chama o MCP, apenas valida config e whitelist.",
    ),
    trust_floor: float = typer.Option(
        8.0,
        "--trust-floor",
        help="TrustScore minimo exigido para recursos whitelist.",
    ),
    row_limit: int = typer.Option(
        50,
        "--row-limit",
        help="Limite de linhas retornadas pelo MCP (guardrail).",
    ),
    byte_limit: int = typer.Option(
        200_000,
        "--byte-limit",
        help="Limite de bytes retornados pelo MCP (guardrail).",
    ),
    whitelist_path: Path = typer.Option(
        Path("config/mcp_resources.json"),
        "--whitelist-path",
        help="Caminho para whitelist local de recursos MCP.",
    ),
    cache_path: Path = typer.Option(
        Path("tmp_meta_test/mcp_docs_cache.json"),
        "--cache-path",
        help="Cache local de respostas MCP.",
    ),
    config_path: Path = typer.Option(
        Path.home() / ".mcp" / "config.toml",
        "--config-path",
        help="Caminho do arquivo de config MCP (aba MCP do Codex).",
    ),
    show_whitelist: bool = typer.Option(
        False,
        "--show-whitelist",
        help="Lista recursos whitelisted e sai.",
    ),
    list_remote: bool = typer.Option(
        False,
        "--list-remote",
        help="Lista recursos remotos via MCP (usa cache se disponivel).",
    ),
) -> None:
    """
    Consulta MCP Context7 para recursos oficiais de docs.
    """
    client = Context7DocsClient(
        config_path=config_path,
        whitelist_path=whitelist_path,
        cache_path=cache_path,
        trust_score_floor=trust_floor,
        row_limit=row_limit,
        byte_limit=byte_limit,
    )

    if show_whitelist:
        resources = client.list_whitelisted_resources()
        for res in resources:
            typer.echo(f"- {res.id} | {res.title} | trustScore={res.trust_score}")
        return

    if list_remote:
        resources = client.list_remote_resources(refresh_cache=True)
        if not resources:
            typer.echo("Nenhum recurso retornado pelo MCP remoto (verifique token ou rede).")
            raise typer.Exit(code=1)
        for res in resources:
            typer.echo(f"- {res.id} | {res.title} | trustScore={res.trust_score}")
        return

    try:
        result = client.search(
            resource_id=resource,
            query=query,
            max_snippets=max_snippets,
            allow_unlisted=allow_unlisted,
            dry_run=dry_run,
            refresh_remote=refresh_remote,
        )
    except MCPConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except MCPRemoteError as exc:
        typer.echo(f"Falha ao consultar MCP: {exc}")
        raise typer.Exit(code=1)

    typer.echo(json.dumps(result, indent=2))


def main() -> None:
    """
    Console script entrypoint (pyproject.toml aponta para esta função).
    """
    app()


if __name__ == "__main__":
    main()
