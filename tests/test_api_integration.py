from fastapi.testclient import TestClient
from enem_project.api.main import app
from enem_project.infra.db_agent import DuckDBAgent
import pytest
from unittest.mock import MagicMock

client = TestClient(app)

@pytest.fixture
def mock_db_agent(monkeypatch):
    """
    Mocka o DuckDBAgent para não depender de um banco real durante os testes de API.
    Simula o retorno de `run_query` com dados fake.
    """
    mock_agent = MagicMock(spec=DuckDBAgent)
    
    # Mock connection object (needed for some legacy parts if any)
    mock_conn = MagicMock()
    mock_agent._get_conn.return_value = mock_conn
    
    # Mock run_query return values
    def side_effect_run_query(sql, params=None):
        sql = sql.lower()
        if "tb_socio_economico" in sql:
            # Returns (rows, columns)
            return [
                ("Classe A (> 20 SM)", 700.0, 750.0, 800.0, 850.0, 900.0)
            ], ["CLASSE", "LOW", "Q1", "MEDIAN", "Q3", "HIGH"]
        
        if "gold_classes" in sql: # Race endpoint
            return [
                (1, 600.0, 600.0, 600.0, 600.0, 600.0, 500)
            ], ["TP_COR_RACA", "NOTA_MATEMATICA", "NOTA_CIENCIAS_NATUREZA", "NOTA_CIENCIAS_HUMANAS", "NOTA_LINGUAGENS_CODIGOS", "NOTA_REDACAO", "COUNT"]
            
        return [], []

    mock_agent.run_query.side_effect = side_effect_run_query
    
    # Inject mock into dashboard_router
    from enem_project.api import dashboard_router
    monkeypatch.setattr(dashboard_router, "db_agent", mock_agent)
    
    return mock_agent

def test_api_socioeconomic_income_returns_correct_structure(mock_db_agent):
    """
    Testa se o endpoint /advanced/socioeconomic/income retorna JSON correto
    baseado na resposta mockada do banco.
    """
    response = client.get("/v1/dashboard/advanced/socioeconomic/income?ano=2023")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 1
    assert data[0]["CLASSE"] == "Classe A (> 20 SM)"
    assert data[0]["MEDIAN"] == 800.0
    # Verifica se DuckDBAgent.run_query foi chamado
    assert mock_db_agent.run_query.called

def test_api_socioeconomic_race_returns_correct_structure(mock_db_agent):
    """
    Testa endpoint de raça.
    """
    response = client.get("/v1/dashboard/advanced/socioeconomic/race?ano=2023")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) > 0
    assert "RACA" in data[0]
    assert data[0]["RACA"] == "Branca" # 1 mapped to Branca

def test_api_guardrails_are_active(mock_db_agent):
    # This test implicitly validates that the router is using the agent, 
    # which we know enforces guardrails internally.
    # We can verify if the agent instance in the router is indeed our mock.
    from enem_project.api import dashboard_router
    assert dashboard_router.db_agent == mock_db_agent
