import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status

from ..infra.db_agent import DuckDBAgent
from ..domain.auth_schemas import UserCreate, UserLogin
from ..domain.user_model import UserInDB, User
from ..infra.security_auth import get_password_hash, verify_password
from ..infra.logging import logger


class AuthService:
    def __init__(self):
        # Ensure table exists (lazy check)
        self._bootstrap_db()

    def _bootstrap_db(self):
        """
        Cria a tabela de usuários se não existir.
        """
        agent = DuckDBAgent(read_only=False)
        try:
            sql = """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                email VARCHAR UNIQUE,
                password_hash VARCHAR,
                role VARCHAR,
                is_active BOOLEAN,
                created_at TIMESTAMP
            );
            """
            agent.execute_script(sql)
        except Exception as e:
            logger.error(f"Erro ao inicializar tabela de usuários: {e}")
        finally:
            agent.close()

    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        agent = DuckDBAgent(read_only=True)
        try:
            # Use parameterized query to prevent SQL Injection
            rows, _ = agent.run_query(
                "SELECT * FROM users WHERE email = ?", params=[email]
            )
            if rows:
                row = rows[0]
                # Mapping: id, email, password_hash, role, is_active, created_at
                return UserInDB(
                    id=row[0],
                    email=row[1],
                    hashed_password=row[2],
                    role=row[3],
                    is_active=row[4],
                    created_at=row[5],
                )
            return None
        finally:
            agent.close()

    def create_user(self, user: UserCreate) -> User:
        existing_user = self.get_user_by_email(user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_pw = get_password_hash(user.password)
        user_id = str(uuid.uuid4())
        now = datetime.now()

        agent = DuckDBAgent(read_only=False)
        try:
            sql = """
            INSERT INTO users (id, email, password_hash, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            agent.run_query(
                sql, params=[user_id, user.email, hashed_pw, user.role, True, now]
            )

            return User(
                id=user_id,
                email=user.email,
                role=user.role,
                is_active=True,
                created_at=now,
            )
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create user",
            )
        finally:
            agent.close()

    def authenticate_user(self, user_login: UserLogin) -> UserInDB:
        user = self.get_user_by_email(user_login.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not verify_password(user_login.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
