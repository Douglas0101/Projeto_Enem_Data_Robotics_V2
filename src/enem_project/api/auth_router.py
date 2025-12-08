from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..domain.auth_schemas import Token, UserLogin, UserCreate, TokenData
from ..services.auth_service import AuthService
from ..infra.security_auth import create_access_token, create_refresh_token
from ..domain.user_model import User
from .dependencies import get_current_user
from .limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

def get_auth_service() -> AuthService:
    return AuthService()

@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def signup(request: Request, user_create: UserCreate, service: AuthService = Depends(get_auth_service)):
    return service.create_user(user_create)

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, user_login: UserLogin, service: AuthService = Depends(get_auth_service)):
    user = service.authenticate_user(user_login)
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }

@router.post("/token", response_model=Token, include_in_schema=False)
@limiter.limit("10/minute")
async def login_form(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), service: AuthService = Depends(get_auth_service)):
    """
    Endpoint compatível com OAuth2 Form (Swagger UI).
    """
    user_login = UserLogin(email=form_data.username, password=form_data.password)
    user = service.authenticate_user(user_login)
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }

@router.get("/me", response_model=TokenData)
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    return current_user