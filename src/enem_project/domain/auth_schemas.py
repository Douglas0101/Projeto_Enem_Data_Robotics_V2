from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str


class TokenData(BaseModel):
    email: str | None = None
    role: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(
        ..., min_length=12, description="Senha forte com no mínimo 12 caracteres"
    )
    role: str = "viewer"  # default role
