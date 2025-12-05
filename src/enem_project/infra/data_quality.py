from __future__ import annotations

from pathlib import Path

from duckdb import DuckDBPyConnection

try:
    from soda.scan import Scan

    _SODA_AVAILABLE = True
except ImportError:  # pragma: no cover - dependência opcional para dev
    Scan = None
    _SODA_AVAILABLE = False

from .logging import logger


def run_soda_scan(conn: DuckDBPyConnection) -> int:
    """
    Executa uma varredura de qualidade de dados usando Soda Core.
    Utiliza arquivos de configuração e checks definidos em src/enem_project/config/.
    """
    if not _SODA_AVAILABLE:
        logger.warning(
            "Soda Core não instalado; pulando scan de qualidade (use poetry add soda-core para habilitar)."
        )
        return 0

    scan = Scan()
    scan.set_data_source_name("enem")

    # Injeta a conexão DuckDB existente para evitar reabertura/locks
    scan.add_duckdb_connection(conn, data_source_name="enem")

    config_path = Path(__file__).parents[1] / "config" / "soda_configuration.yml"
    checks_path = Path(__file__).parents[1] / "config" / "checks.yml"

    if not config_path.exists() or not checks_path.exists():
        logger.error(
            f"Arquivos de configuração do Soda não encontrados: {config_path} ou {checks_path}"
        )
        return 1

    scan.add_configuration_yaml_file(str(config_path))
    scan.add_sodacl_yaml_file(str(checks_path))

    logger.info("Iniciando scan de qualidade de dados com Soda Core...")
    exit_code = scan.execute()

    # Log detalhado dos resultados
    logger.info(f"Soda Scan finalizado. Exit code: {exit_code}")
    logger.info(scan.get_logs_text())

    if exit_code != 0:
        # Loga falhas específicas se houver
        for check in scan._checks:
            if check.outcome != "pass":
                logger.error(f"Falha no check: {check}")

    return exit_code


def assert_dashboard_data_checks(conn: DuckDBPyConnection) -> None:
    """
    Quality Gate: Executa Soda Scan e interrompe o pipeline em caso de erro.
    """
    exit_code = run_soda_scan(conn)
    if exit_code > 0:
        raise RuntimeError(
            f"Soda Data Quality Check falhou com código {exit_code}. Verifique os logs."
        )
