# Especificação de Qualidade Industrial: Sistema de Autenticação e Autorização (Enem Data Robotics V2)

## 1. Objetivo
Este documento define os padrões técnicos, arquiteturais e de segurança para a implementação do subsistema de Login e Gestão de Identidade do projeto **Enem Data Robotics V2**. O objetivo é garantir uma implementação de "Qualidade Industrial", focada em segurança (OWASP Top 10), performance, escalabilidade e conformidade com a LGPD.

---

## 2. Arquitetura de Autenticação

O sistema utilizará o padrão **OAuth 2.0 com JWT (JSON Web Tokens)**, garantindo *statelessness* para facilitar a escalabilidade horizontal do backend (FastAPI) e integração fluida com o frontend (React).

### 2.1. Componentes Principais
1.  **Protocolo:** OAuth 2.0 Password Grant Flow (adequado para clientes first-party).
2.  **Tokens:**
    *   **Access Token:** JWT assinado, curto tempo de vida (15 a 30 minutos). Contém claims básicos (`sub`, `role`, `exp`, `iat`).
    *   **Refresh Token:** Token opaco ou JWT de longa duração (7 dias), armazenado de forma segura no banco de dados (hash) e no cliente.
3.  **Algoritmo de Assinatura:** `HS256` (HMAC SHA-256) com chave secreta rotacionável gerenciada via variáveis de ambiente (`SECRET_KEY`).

---

## 3. Requisitos Funcionais

### 3.1. Login (Autenticação)
*   **Entrada:** E-mail e Senha.
*   **Processo:**
    *   Validação de formato de e-mail (Pydantic `EmailStr`).
    *   Verificação de senha contra hash armazenado.
    *   Geração do par de tokens (Access + Refresh).
*   **Saída:** JSON contendo `access_token`, `token_type` e `refresh_token` (ou setado via Cookie HttpOnly).

### 3.2. Refresh Token
*   **Entrada:** Refresh Token válido.
*   **Processo:** Validação do token e verificação se não foi revogado no banco de dados.
*   **Saída:** Novo `access_token`.

### 3.3. Logout
*   **Processo:** Invalidação do Refresh Token no banco de dados (Allowlist/Blocklist).
*   **Frontend:** Limpeza do armazenamento local/cookies.

### 3.4. Cadastro de Usuário (Sign Up)
*   **Regras de Senha:** Mínimo 12 caracteres, contendo maiúsculas, minúsculas, números e símbolos (NIST guidelines).
*   **Unicidade:** E-mail deve ser único no sistema.

---

## 4. Requisitos Não-Funcionais (Padrão Industrial)

### 4.1. Segurança Criptográfica
*   **Hashing de Senha:** **NÃO** usar MD5 ou SHA simples.
    *   **Padrão:** `Argon2` (recomendado) ou `Bcrypt`.
    *   **Biblioteca:** `passlib[argon2]` ou `bcrypt`.
*   **Segredos:** A `SECRET_KEY` deve ter entropia alta (min 32 bytes) e ser carregada via `python-dotenv` ou Secret Manager.

### 4.2. Proteção Contra Ataques (OWASP)
*   **Rate Limiting:** Implementar limitação de tentativas de login por IP/Usuário para prevenir *Brute Force* e *Credential Stuffing*.
    *   *Ferramenta Sugerida:* `slowapi` (já presente no `pyproject.toml`).
*   **SQL Injection:** Uso estrito de ORM (se houver) ou parâmetros bindados no DuckDB/SQLAlchemy.
*   **XSS (Cross-Site Scripting):** O Frontend não deve armazenar tokens sensíveis em `localStorage` se houver risco de XSS. Preferência por **Cookies HttpOnly, Secure, SameSite=Strict**.

### 4.3. Observabilidade e Auditoria
*   **Logs:** Todos os eventos de login (sucesso/falha) devem ser logados via `loguru` com contexto (IP mascarado, Timestamp, User ID).
    *   *Alerta:* Falhas consecutivas devem gerar alertas de segurança.
*   **Traceability:** O `correlation_id` deve persistir durante o fluxo de autenticação.

---

## 5. Especificação Técnica de Implementação

### 5.1. Estrutura de Arquivos (Backend)

A implementação deve seguir a estrutura modular do projeto:

```
src/enem_project/
├── api/
│   └── auth_router.py       # Endpoints: /login, /refresh, /me
├── domain/
│   ├── auth_schemas.py      # Pydantic Models (Token, UserLogin, UserCreate)
│   └── user_model.py        # Entidade de Usuário
├── infra/
│   └── security_auth.py     # Funções: verify_password, get_password_hash, create_access_token
└── services/
    └── auth_service.py      # Lógica de negócio: authenticate_user, create_user
```

### 5.2. Estrutura de Banco de Dados (DuckDB/Postgres)

Tabela `users`:
*   `id` (UUID/Integer): Chave primária.
*   `email` (String): Índice único.
*   `password_hash` (String): Hash Argon2.
*   `role` (Enum): 'admin', 'analyst', 'viewer'.
*   `is_active` (Boolean).
*   `created_at` (Timestamp).

### 5.3. Exemplo de Dependência (FastAPI)

```python
# src/enem_project/api/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from src.enem_project.config.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    # Aqui buscaria o usuário no DB...
```

---

## 6. Plano de Testes

Para garantir a qualidade industrial, os seguintes testes são mandatórios:

1.  **Unitários:**
    *   Hashing de senha (verificar se hash muda para mesma senha com salts diferentes).
    *   Geração e expiração de tokens JWT.
2.  **Integração:**
    *   Fluxo completo: Cadastro -> Login -> Acesso a Rota Protegida -> Logout.
    *   Teste de Refresh Token expirado.
3.  **Segurança (Security Testing):**
    *   Tentar acessar rota protegida sem token (Deve retornar 401).
    *   Tentar usar token expirado (Deve retornar 401).
    *   Tentar login com senha incorreta repetidamente (Verificar Rate Limiting).

---

## 7. Checklist de Entrega

- [ ] Biblioteca `passlib` e `python-jose` (ou `pyjwt`) adicionadas ao `pyproject.toml`.
- [ ] Variáveis `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` no `.env`.
- [ ] Router de Autenticação configurado no `main.py`.
- [ ] Middleware de Rate Limiting ativo nas rotas de auth.
- [ ] Testes automatizados cobrindo "Caminho Feliz" e "Casos de Erro".
