from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from enem_project.infra.data_quality import assert_dashboard_data_checks


@pytest.fixture
def mock_db_connection():
    """Mock de conexão do DuckDB para passar para as funções de check."""
    return MagicMock()


@patch("enem_project.infra.data_quality.run_soda_scan")
def test_assert_dashboard_data_checks_success(mock_run_soda, mock_db_connection):
    """
    Testa se assert_dashboard_data_checks passa silenciosamente quando o Soda Scan
    retorna código de saída 0 (sucesso).
    """
    # Configura o mock para retornar 0 (sucesso)
    mock_run_soda.return_value = 0

    try:
        assert_dashboard_data_checks(mock_db_connection)
    except RuntimeError:
        pytest.fail(
            "assert_dashboard_data_checks levantou RuntimeError inesperadamente com exit_code=0"
        )

    mock_run_soda.assert_called_once_with(mock_db_connection)


@patch("enem_project.infra.data_quality.run_soda_scan")
def test_assert_dashboard_data_checks_failure(mock_run_soda, mock_db_connection):
    """
    Testa se assert_dashboard_data_checks levanta RuntimeError quando o Soda Scan
    retorna código de saída > 0 (falha).
    """
    # Configura o mock para retornar 1 (falha)
    mock_run_soda.return_value = 1

    with pytest.raises(RuntimeError) as excinfo:
        assert_dashboard_data_checks(mock_db_connection)

    assert "Soda Data Quality Check falhou com código 1" in str(excinfo.value)
    mock_run_soda.assert_called_once_with(mock_db_connection)
