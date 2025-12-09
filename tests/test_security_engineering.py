import pytest
from fastapi.testclient import TestClient
from argon2.exceptions import VerifyMismatchError
import duckdb
from enem_project.api.main import app
from enem_project.infra.security_auth import ph
from enem_project.infra.db_agent import DuckDBAgent

client = TestClient(app)

def test_argon2_industrial_configuration():
    """
    CONFIRMAÇÃO DE QUALIDADE: Hashing Robusto
    Valida se o Argon2id está configurado com parâmetros de robustez industrial
    conforme definido no Plano Diretor de Cibersegurança e Escalabilidade.
    
    Requisito 2.1: "memory_cost=65536, time_cost=2 e parallelism=2"
    """
    expected_time_cost = 2
    expected_memory_cost = 65536
    expected_parallelism = 2
    
    assert ph.time_cost == expected_time_cost, f"Time cost deve ser {expected_time_cost}"
    assert ph.memory_cost == expected_memory_cost, f"Memory cost deve ser {expected_memory_cost} (64MB)"
    assert ph.parallelism == expected_parallelism, f"Parallelism deve ser {expected_parallelism}"
    
    # Validação Funcional
    senha_teste = "EngenhariaDeDados2025!"
    hash_gerado = ph.hash(senha_teste)
    
    # Verifica senha correta (retorna True ou None, não deve lançar erro)
    assert ph.verify(hash_gerado, senha_teste)
    
    # Verifica senha errada (deve lançar VerifyMismatchError)
    with pytest.raises(VerifyMismatchError):
        ph.verify(hash_gerado, "senha_errada")

def test_duckdb_resource_isolation_readonly(tmp_path):
    """
    CONFIRMAÇÃO DE QUALIDADE: Isolamento de Recursos
    Valida se o DuckDBAgent em modo read_only bloqueia escritas.
    
    Requisito 5.1: "A API deve instanciar o agente de banco de dados estritamente como read_only=True"
    """
    # Setup: Cria um banco temporário para o teste (DuckDB exige que o arquivo exista para RO)
    db_file = tmp_path / "test_security.duckdb"
    conn_setup = duckdb.connect(str(db_file))
    conn_setup.execute("CREATE TABLE valid_table (id INTEGER)")
    conn_setup.close()

    # Instancia explicitamente em modo leitura apontando para o banco temporário
    agent = DuckDBAgent(db_path=db_file, read_only=True)
    
    # 1. Teste via Guardrail de Script (nível Aplicação)
    with pytest.raises(ValueError) as excinfo:
        agent.execute_script("CREATE TABLE hacker (id int)")
    assert "não é possível executar scripts ddl em modo read-only" in str(excinfo.value).lower()

    # 2. Teste via Conexão Direta (nível Infraestrutura/Driver)
    # Tentamos burlar o guardrail de string usando o cursor direto
    conn = agent.get_connection()
    with pytest.raises(duckdb.Error) as excinfo_db:
        conn.execute("CREATE TABLE hacker_bypass (id int)")
    
    # Mensagem de erro do DuckDB para violação de read-only varia, mas geralmente contém "read access" ou "read-only"
    error_msg = str(excinfo_db.value).lower()
    assert "read" in error_msg or "access" in error_msg, f"Erro inesperado do DB: {error_msg}"

    agent.close()

def test_rate_limiting_protection():
    """
    CONFIRMAÇÃO DE QUALIDADE: Hardening da API (Rate Limiting)
    Simula um ataque de força bruta para validar a proteção contra DDoS/Brute Force.
    
    Requisito 4.2: "Proteção contra força bruta e DDoS na camada de API"
    """
    # O endpoint /health tem limite de 100/minute
    # O endpoint /auth/login tem limite de 10/minute (definido em auth_router.py)
    
    # Mockando IP para garantir isolamento deste teste
    ip_atacante = "203.0.113.42"
    headers = {"X-Forwarded-For": ip_atacante}
    
    payload = {"email": "attacker@evil.com", "password": "123"}
    
    limit = 10
    blocked = False
    
    # Tenta exceder o limite (Limit + 5 tentativas)
    for i in range(limit + 5):
        response = client.post("/auth/login", json=payload, headers=headers)
        if response.status_code == 429:
            blocked = True
            assert "Rate limit exceeded" in response.text or "Muitas requisições" in response.text
            break
            
    assert blocked, "FALHA CRÍTICA: O Rate Limiting não bloqueou o ataque simulado."
