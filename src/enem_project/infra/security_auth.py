from datetime import datetime, timedelta, timezone
from typing import Union

from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ..config.settings import settings

# Configuração de Qualidade Industrial para Argon2id
# Referência OWASP: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#argon2id
# - time_cost=2: Número de iterações.
# - memory_cost=65536: 64 MiB de memória (aumenta custo para ASICs/GPUs).
# - parallelism=2: Threads paralelas.
ph = PasswordHasher(
    time_cost=2, 
    memory_cost=65536, 
    parallelism=2, 
    hash_len=32, 
    salt_len=16
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha em texto plano corresponde ao hash Argon2id armazenado.
    Utiliza a biblioteca nativa argon2-cffi para evitar warnings de depreciação do passlib.
    """
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        # Defesa em profundidade: falha segura para qualquer outro erro de verificação
        return False


def get_password_hash(password: str) -> str:
    """
    Gera um hash Argon2id robusto para a senha.
    Argon2id é resistente a ataques de canal lateral e ataques baseados em GPU.
    """
    return ph.hash(password)


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """
    Cria um token de acesso JWT assinado.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """
    Cria um refresh token JWT (longa duração).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt