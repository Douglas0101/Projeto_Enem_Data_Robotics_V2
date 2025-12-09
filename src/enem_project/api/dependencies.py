import os
from typing import Generator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError

from ..infra.db_agent import DuckDBAgent
from ..infra.logging import logger
from ..config.settings import settings
from ..domain.auth_schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_db_agent() -> Generator[DuckDBAgent, None, None]:
    """
    Dependency provider for DuckDBAgent.
    Ensures proper resource management in the FastAPI dependency lifecycle.
    Includes Enterprise Performance Tuning PRAGMAs.
    """
    # Create an agent in read-only mode for dashboard/API usage.
    agent = DuckDBAgent(read_only=True)

    # --- Enterprise Tuning ---
    try:
        conn = agent.get_connection()

        # Configurações via Variáveis de Ambiente ou Defaults Industriais
        mem_limit = os.getenv("DUCKDB_MEMORY_LIMIT", "4GB")
        threads = os.getenv("DUCKDB_THREADS", "4")
        temp_dir = os.getenv("DUCKDB_TEMP_DIR", "/tmp/duckdb_spill")  # nosec B108

        # Aplicação segura dos PRAGMAs
        # Nota: Em DuckDB read-only, alguns PRAGMAs globais podem ser ignorados ou requerem init config.
        # Mas memory_limit e threads geralmente podem ser ajustados por sessão/conexão.
        conn.execute(f"PRAGMA memory_limit='{mem_limit}'")
        conn.execute(f"PRAGMA threads={threads}")
        conn.execute(f"PRAGMA temp_directory='{temp_dir}'")

        logger.debug(
            f"DuckDB Tuning Applied: Mem={mem_limit}, Threads={threads}, Temp={temp_dir}"
        )

    except Exception as e:
        logger.warning(f"Failed to apply DuckDB tuning PRAGMAs: {e}")

    try:
        yield agent
    finally:
        # Although DuckDBAgent currently relies on internal connection pooling/checking,
        # calling close() ensures we release resources if the implementation changes
        # to use dedicated connections per request in the future.
        agent.close()


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenData:
    """
    Valida o token JWT e retorna os dados do usuário (sub/email).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, role=role)
    except PyJWTError:
        raise credentials_exception
    return token_data
