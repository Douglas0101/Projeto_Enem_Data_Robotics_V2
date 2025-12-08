from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from enem_project.api.main import app
from enem_project.infra.security_auth import get_password_hash

client = TestClient(app)

@pytest.fixture
def mock_db_agent():
    with patch("enem_project.services.auth_service.DuckDBAgent") as MockAgent:
        yield MockAgent

def test_signup_success(mock_db_agent):
    mock_instance = mock_db_agent.return_value
    # get_user_by_email -> empty list (user not found)
    mock_instance.run_query.return_value = ([], []) 
    
    payload = {
        "email": "newuser@example.com",
        "password": "StrongPassword123!",
        "role": "viewer"
    }
    response = client.post("/auth/signup", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "password" not in data  # Should not return password

def test_signup_duplicate_email(mock_db_agent):
    mock_instance = mock_db_agent.return_value
    # get_user_by_email -> returns a row (user exists)
    # Row structure: id, email, password_hash, role, is_active, created_at
    mock_instance.run_query.return_value = (
        [("uuid-123", "existing@example.com", "hash", "viewer", True, "2023-01-01")], 
        []
    )
    
    payload = {
        "email": "existing@example.com",
        "password": "StrongPassword123!"
    }
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_success(mock_db_agent):
    mock_instance = mock_db_agent.return_value
    
    hashed_pw = get_password_hash("Secret123!")
    # get_user_by_email returns user
    mock_instance.run_query.return_value = (
        [("uuid-123", "user@example.com", hashed_pw, "viewer", True, "2023-01-01")], 
        []
    )
    
    payload = {"email": "user@example.com", "password": "Secret123!"}
    response = client.post("/auth/login", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(mock_db_agent):
    mock_instance = mock_db_agent.return_value
    
    hashed_pw = get_password_hash("Secret123!")
    mock_instance.run_query.return_value = (
        [("uuid-123", "user@example.com", hashed_pw, "viewer", True, "2023-01-01")], 
        []
    )
    
    payload = {"email": "user@example.com", "password": "WrongPassword"}
    response = client.post("/auth/login", json=payload)
    
    assert response.status_code == 401

def test_access_protected_route(mock_db_agent):
    # 1. Login to get token
    mock_instance = mock_db_agent.return_value
    hashed_pw = get_password_hash("Secret123!")
    mock_instance.run_query.return_value = (
        [("uuid-123", "user@example.com", hashed_pw, "admin", True, "2023-01-01")], 
        []
    )
    
    login_res = client.post("/auth/login", json={"email": "user@example.com", "password": "Secret123!"})
    token = login_res.json()["access_token"]
    
    # 2. Access protected route
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)
    
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert response.json()["role"] == "admin"
