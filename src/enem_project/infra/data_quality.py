from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from duckdb import DuckDBPyConnection

from .logging import logger


@dataclass(frozen=True)
class DataCheckResult:
    """
    Resultado estruturado de uma checagem de dados.
    """

    name: str
    passed: bool
    severity: str  # "error" ou "warning"
    details: str = ""


def _check_row_count_positive(
    conn: DuckDBPyConnection,
    table: str,
    *,
    min_rows: int = 1,
) -> DataCheckResult:
    row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    passed = row_count >= min_rows
    return DataCheckResult(
        name=f"{table}.row_count>= {min_rows}",
        passed=passed,
        severity="error",
        details=f"row_count={row_count}",
    )


def _check_notas_range(
    conn: DuckDBPyConnection,
    table: str,
    columns: Iterable[str],
    *,
    min_allowed: float = 0.0,
    max_allowed: float = 1000.0,
) -> DataCheckResult:
    """
    Garante que colunas de nota estejam dentro do intervalo esperado
    [min_allowed, max_allowed], ignorando nulos.
    """
    conditions = [
        f"{col} < {min_allowed} OR {col} > {max_allowed}"
        for col in columns
    ]
    where_clause = " OR ".join(conditions)
    sql = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
    out_of_range = conn.execute(sql).fetchone()[0]
    passed = out_of_range == 0
    return DataCheckResult(
        name=f"{table}.notas_in_range[{min_allowed},{max_allowed}]",
        passed=passed,
        severity="error",
        details=f"out_of_range_rows={out_of_range}",
    )


def run_dashboard_data_checks(conn: DuckDBPyConnection) -> List[DataCheckResult]:
    """
    Executa checagens mínimas de qualidade sobre as tabelas de dashboard
    no backend SQL (DuckDB).

    As regras seguem o guia de testes de dados profissionais:
        - row_count > 0 para tabelas principais;
        - notas em intervalos plausíveis [0, 1000].
    """
    checks: list[DataCheckResult] = []

    # Tabelas obrigatórias
    for table in ("tb_notas", "tb_notas_stats", "tb_notas_geo"):
        checks.append(_check_row_count_positive(conn, table, min_rows=1))

    # Faixas de notas em tb_notas_stats (agregados anuais).
    nota_prefixes = [
        "NOTA_CIENCIAS_NATUREZA",
        "NOTA_CIENCIAS_HUMANAS",
        "NOTA_LINGUAGENS_CODIGOS",
        "NOTA_MATEMATICA",
        "NOTA_REDACAO",
    ]
    range_columns_stats = [
        f"{prefix}_{suffix}"
        for prefix in nota_prefixes
        for suffix in ("min", "max", "mean")
    ]
    checks.append(
        _check_notas_range(
            conn,
            "tb_notas_stats",
            range_columns_stats,
            min_allowed=0.0,
            max_allowed=1000.0,
        ),
    )

    # Faixas de notas em tb_notas_geo (médias geográficas).
    range_columns_geo = [f"{prefix}_mean" for prefix in nota_prefixes]
    checks.append(
        _check_notas_range(
            conn,
            "tb_notas_geo",
            range_columns_geo,
            min_allowed=0.0,
            max_allowed=1000.0,
        ),
    )

    # Log estruturado do resultado
    for check in checks:
        level = "success" if check.passed else "error"
        log_fn = getattr(logger, level, logger.info)
        log_fn(
            "[data-quality] %s | passed=%s | severity=%s | %s",
            check.name,
            check.passed,
            check.severity,
            check.details,
        )

    return checks


def assert_dashboard_data_checks(conn: DuckDBPyConnection) -> None:
    """
    Executa as checagens e lança exceção se algum check crítico (severity=error)
    falhar. Esse método é adequado para ser usado como quality gate em
    workflows ou no startup da API.
    """
    checks = run_dashboard_data_checks(conn)
    failing = [c for c in checks if not c.passed and c.severity == "error"]
    if failing:
        summary = "; ".join(f"{c.name} ({c.details})" for c in failing)
        raise RuntimeError(f"Falhas em checks de dados do dashboard: {summary}")

