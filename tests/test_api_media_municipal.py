"""
Testes específicos para o endpoint /media-municipal.
"""
from typing import Any
from unittest.mock import Mock
import pytest
from fastapi import Request

# Import the module under test
import enem_project.api.dashboard_router as dr


class FakeAgentMedia:
    """Mock agent for Media Municipal tests."""

    def __init__(self):
        self.calls = []

    def run_query(self, sql: str, params: list[Any] | None = None):
        self.calls.append((sql, params))
        # Simple mock response
        # Columns must match the SELECT alias in dashboard_router.py
        columns = [
            "NO_MUNICIPIO_PROVA",
            "ANO",
            "MEDIA_CN",
            "MEDIA_CH",
            "MEDIA_LC",
            "MEDIA_MT",
            "MEDIA_RED",
            "MEDIA_FINAL",
            "QTD_ALUNOS"
        ]

        # Mock data row
        row = (
            "São Paulo",  # NO_MUNICIPIO_PROVA
            2023,        # ANO
            600.0,       # CN
            610.0,       # CH
            620.0,       # LC
            630.0,       # MT
            640.0,       # RED
            620.0,       # FINAL (Average)
            1000         # QTD_ALUNOS
        )
        return [row], columns


@pytest.mark.asyncio
async def test_get_media_municipal_success():
    """Test successful response from get_media_municipal."""
    mock_request = Mock(spec=Request)
    fake_agent = FakeAgentMedia()

    # Call the endpoint function directly
    # Note: depends on the router function signature
    res = await dr.get_media_municipal(
        request=mock_request,
        agent=fake_agent,
        uf="SP",
        municipio="Sao Paulo",
        ano_inicio=2020,
        ano_fim=2023,
        min_alunos=50
    )

    # Check results
    assert len(res) == 1
    item = res[0]

    # Verify field access (Pydantic model or dict-like object)
    # The endpoint returns MediaMunicipalRow objects
    assert item.NO_MUNICIPIO_PROVA == "São Paulo"
    assert item.ANO == 2023
    assert item.MEDIA_FINAL == 620.0
    assert item.QTD_ALUNOS == 1000

    # Verify query params
    # Check if WHERE clauses were constructed correctly
    sql_call = fake_agent.calls[0][0]
    params_call = fake_agent.calls[0][1]

    assert "gold_tb_notas_geo" in sql_call
    assert "NOTA_REDACAO_count >= ?" in sql_call

    # Check params order: UF, Muni, AnoStart, AnoEnd, MinAlunos
    # UF is normalized to upper
    assert "SP" in params_call
    # Normalize text should have happened (SAO PAULO)
    assert "SAO PAULO" in params_call
    assert 2020 in params_call
    assert 2023 in params_call
    assert 50 in params_call
