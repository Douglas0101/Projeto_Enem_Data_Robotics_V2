import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..infra.logging import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware que adiciona um ID único (UUID) para cada requisição.
    Isso facilita o rastreamento de logs distribuídos (correlation ID).
    O ID é retornado no header 'X-Request-ID'.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        
        # Adiciona o ID ao contexto do logger (se usar estruturado)
        # ou apenas disponibiliza para uso.
        # Aqui vamos injetar no request state para acesso posterior.
        request.state.request_id = request_id
        
        start_time = time.perf_counter()
        
        # Processa a requisição
        try:
            response = await call_next(request)
        except Exception as e:
            # Se ocorrer erro no processamento, garante que o erro seja logado com o ID
            process_time = time.perf_counter() - start_time
            logger.error(f"Request {request_id} failed after {process_time:.4f}s: {e}")
            raise e

        process_time = time.perf_counter() - start_time
        
        # Adiciona o header na resposta
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Loga a conclusão (opcional, pode ser verboso)
        # logger.info(f"Request {request_id} completed in {process_time:.4f}s")
        
        return response
