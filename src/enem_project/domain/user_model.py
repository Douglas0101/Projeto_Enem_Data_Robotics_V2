from datetime import datetime
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """
    Modelo de domínio para Usuário.
    """

    id: str  # UUID
    email: EmailStr
    role: str = "viewer"
    is_active: bool = True
    created_at: datetime = datetime.now()


class UserInDB(User):
    """
    Modelo estendido para persistência (inclui hash da senha).
    """

    hashed_password: str
