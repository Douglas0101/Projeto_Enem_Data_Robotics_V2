from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request


class FakeAgent:
    """Agente de teste que responde com dados mínimos para as rotas do dashboard."""

    def __init__(self):
        self.calls: list[str] = []

    def _get_conn(self) -> object:  # pragma: no cover - compat
        return object()

    def run_query(self, sql: str, params: list[Any] | None = None):
        self.calls.append(sql)
        sql_lower = sql.lower()

        if "distinct ano" in sql_lower:
            return [(2024,)], ["ANO"]

        if "from tb_notas_stats" in sql_lower:
            columns = [
                "ANO",
                "TOTAL_INSCRITOS",
                "IDADE_mean",
                "IDADE_std",
                "IDADE_min",
                "IDADE_median",
                "IDADE_max",
                "NOTA_CIENCIAS_NATUREZA_count",
                "NOTA_CIENCIAS_NATUREZA_mean",
                "NOTA_CIENCIAS_NATUREZA_std",
                "NOTA_CIENCIAS_NATUREZA_min",
                "NOTA_CIENCIAS_NATUREZA_median",
                "NOTA_CIENCIAS_NATUREZA_max",
                "NOTA_CIENCIAS_HUMANAS_count",
                "NOTA_CIENCIAS_HUMANAS_mean",
                "NOTA_CIENCIAS_HUMANAS_std",
                "NOTA_CIENCIAS_HUMANAS_min",
                "NOTA_CIENCIAS_HUMANAS_median",
                "NOTA_CIENCIAS_HUMANAS_max",
                "NOTA_LINGUAGENS_CODIGOS_count",
                "NOTA_LINGUAGENS_CODIGOS_mean",
                "NOTA_LINGUAGENS_CODIGOS_std",
                "NOTA_LINGUAGENS_CODIGOS_min",
                "NOTA_LINGUAGENS_CODIGOS_median",
                "NOTA_LINGUAGENS_CODIGOS_max",
                "NOTA_MATEMATICA_count",
                "NOTA_MATEMATICA_mean",
                "NOTA_MATEMATICA_std",
                "NOTA_MATEMATICA_min",
                "NOTA_MATEMATICA_median",
                "NOTA_MATEMATICA_max",
                "NOTA_REDACAO_count",
                "NOTA_REDACAO_mean",
                "NOTA_REDACAO_std",
                "NOTA_REDACAO_min",
                "NOTA_REDACAO_median",
                "NOTA_REDACAO_max",
            ]
            rows = [
                (
                    2024,
                    1000,
                    18.0,
                    1.0,
                    16.0,
                    18.0,
                    22.0,
                    1000,
                    600.0,
                    10.0,
                    500.0,
                    600.0,
                    700.0,
                    1000,
                    610.0,
                    11.0,
                    500.0,
                    610.0,
                    710.0,
                    1000,
                    620.0,
                    12.0,
                    500.0,
                    620.0,
                    720.0,
                    1000,
                    630.0,
                    13.0,
                    500.0,
                    630.0,
                    730.0,
                    1000,
                    640.0,
                    14.0,
                    500.0,
                    640.0,
                    740.0,
                )
            ]
            return rows, columns

        if "from tb_notas_geo_uf" in sql_lower:
            columns = [
                "ANO",
                "SG_UF_PROVA",
                "INSCRITOS",
                "NOTA_CIENCIAS_NATUREZA_count",
                "NOTA_CIENCIAS_NATUREZA_mean",
                "NOTA_CIENCIAS_HUMANAS_count",
                "NOTA_CIENCIAS_HUMANAS_mean",
                "NOTA_LINGUAGENS_CODIGOS_count",
                "NOTA_LINGUAGENS_CODIGOS_mean",
                "NOTA_MATEMATICA_count",
                "NOTA_MATEMATICA_mean",
                "NOTA_REDACAO_count",
                "NOTA_REDACAO_mean",
            ]
            rows = [
                (2024, "SP", 500, 500, 610.0, 500, 620.0, 500, 630.0, 500, 640.0, 500, 650.0),
                # Linha com contagens em float e campo ausente (será preenchido com None)
                (2024, "RJ", 200.0, 100.5, 600.0, 100.5, 610.0, 100.5, 620.0, 100.5, 630.0, None, None),
            ]
            return rows, columns

        if "from tb_notas_geo" in sql_lower:
            columns = [
                "ANO",
                "SG_UF_PROVA",
                "CO_MUNICIPIO_PROVA",
                "NO_MUNICIPIO_PROVA",
                "NOTA_CIENCIAS_NATUREZA_count",
                "NOTA_CIENCIAS_NATUREZA_mean",
                "NOTA_CIENCIAS_HUMANAS_count",
                "NOTA_CIENCIAS_HUMANAS_mean",
                "NOTA_LINGUAGENS_CODIGOS_count",
                "NOTA_LINGUAGENS_CODIGOS_mean",
                "NOTA_MATEMATICA_count",
                "NOTA_MATEMATICA_mean",
                "NOTA_REDACAO_count",
                "NOTA_REDACAO_mean",
            ]
            rows = [
                (
                    2024,
                    "SP",
                    "3550308",
                    "São Paulo",
                    120,
                    620.0,
                    120,
                    630.0,
                    120,
                    640.0,
                    120,
                    650.0,
                    120,
                    660.0,
                )
            ]
            return rows, columns

        if "from tb_notas_histogram" in sql_lower:
            columns = ["ANO", "DISCIPLINA", "BIN_START", "BIN_END", "CONTAGEM"]
            rows = [(2024, "MATEMATICA", 400.0, 450.0, 10)]
            return rows, columns

        if "tb_socio_economico" in sql_lower:
            columns = ["CLASSE", "LOW", "Q1", "MEDIAN", "Q3", "HIGH"]
            rows = [("Classe A (> 20 SM)", 700.0, 750.0, 800.0, 850.0, 900.0)]
            return rows, columns

        if "gold_classes" in sql_lower:
            columns = [
                "TP_COR_RACA",
                "NOTA_MATEMATICA",
                "NOTA_CIENCIAS_NATUREZA",
                "NOTA_CIENCIAS_HUMANAS",
                "NOTA_LINGUAGENS_CODIGOS",
                "NOTA_REDACAO",
                "COUNT",
            ]
            rows = [(1, 600.0, 600.0, 600.0, 600.0, 600.0, 500)]
            return rows, columns

        return [], []


@pytest.fixture
def patched_router(monkeypatch):
    # Evita workflow pesado no lifespan
    monkeypatch.setenv("ENEM_SKIP_LIFESPAN", "1")

    import enem_project.api.dashboard_router as dr

    # Limpa caches das rotas para evitar reuso entre testes
    for fn in (
        dr.get_notas_stats,
        dr.get_notas_geo,
        dr.get_notas_geo_uf,
        dr.get_notas_histograma,
        dr.get_anos_disponiveis,
        dr.get_socioeconomic_income,
        dr.get_socioeconomic_race,
        dr.get_radar_data,
    ):
        if hasattr(fn, "cache_clear"):
            fn.cache_clear()

    return dr


@pytest.fixture
def test_app(patched_router):
    app = FastAPI(
        title="ENEM Data Robotics API",
        version="1.0.0",
        description="API analítica para consumo profissional dos dados do projeto ENEM Data Robotics (camadas silver/gold e tabelas de dashboard).",
    )
    app.include_router(patched_router.router)
    return app


def test_openapi_available(test_app: FastAPI):
    schema = test_app.openapi()
    assert schema["info"]["title"] == "ENEM Data Robotics API"



def test_notas_stats(patched_router):
    mock_request = Mock(spec=Request)
    fake_agent = FakeAgent()
    # Pass request and agent as required by the new signature
    body = patched_router.get_notas_stats(mock_request, fake_agent, ano_inicio=2024, ano_fim=2024)
    # Result is a coroutine because functions are async
    import asyncio
    body = asyncio.run(body)
    
    assert len(body) == 1
    assert body[0].ANO == 2024
    assert body[0].NOTA_MATEMATICA_mean == 630.0


def test_notas_geo(patched_router):
    mock_request = Mock(spec=Request)
    fake_agent = FakeAgent()
    body = patched_router.get_notas_geo(mock_request, fake_agent, ano=[2024], min_count=10, limit=5, page=1)
    import asyncio
    body = asyncio.run(body)
    
    assert len(body) == 1
    assert body[0].SG_UF_PROVA == "SP"
    assert body[0].NO_MUNICIPIO_PROVA == "São Paulo"


def test_notas_geo_uf(patched_router):
    mock_request = Mock(spec=Request)
    fake_agent = FakeAgent()
    body = patched_router.get_notas_geo_uf(mock_request, fake_agent, ano=2024, min_inscritos=100)
    import asyncio
    body = asyncio.run(body)
    
    assert len(body) == 1
    assert body[0].SG_UF_PROVA == "SP"
    assert body[0].INSCRITOS == 500


def test_notas_histograma(patched_router):
    mock_request = Mock(spec=Request)
    fake_agent = FakeAgent()
    body = patched_router.get_notas_histograma(mock_request, fake_agent, ano=2024, disciplina="MATEMATICA")
    import asyncio
    body = asyncio.run(body)
    
    assert len(body) == 1
    assert body[0].DISCIPLINA == "MATEMATICA"
    assert body[0].CONTAGEM == 10
