import time
import uuid
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import parse_qs

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..infra.logging import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware de Auditoria e Rastreabilidade.
    Gera logs estruturados (JSON-friendly via loguru serialize) para cada requisição,
    contendo metadados vitais para segurança e observabilidade.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Gerar Request ID (Correlation ID)
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Captura Timestamp inicial
        start_time = time.perf_counter()
        
        # Preparar metadados de auditoria (Pré-execução)
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        
        # Sanitização de Query Params (Remover dados sensíveis se houver)
        # Simples remoção de chaves que possam conter segredos (ex: 'token', 'key')
        raw_query = request.url.query
        sanitized_params = {}
        if raw_query:
            parsed = parse_qs(raw_query)
            for key, values in parsed.items():
                if any(secret in key.lower() for secret in ['token', 'key', 'pass', 'secret']):
                    sanitized_params[key] = '[REDACTED]'
                else:
                    sanitized_params[key] = values[0] if len(values) == 1 else values

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            # Re-raise para o Exception Handler Global lidar, mas logamos o erro aqui também se necessário
            # O handler global cuidará da resposta JSON de erro.
            raise e
        finally:
            # Calculo de tempo de execução
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Structured Log Context
            # Utiliza logger.bind para anexar campos extras que o loguru pode serializar em JSON
            audit_logger = logger.bind(
                audit=True,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                request_id=request_id,
                client_ip=client_ip,
                endpoint=endpoint,
                query_params=sanitized_params,
                execution_time_ms=round(execution_time_ms, 2),
                http_status=status_code
            )
            
            # Log Final
            audit_logger.info(f"AUDIT: {request.method} {endpoint} - {status_code} - {execution_time_ms:.2f}ms")

            # Injeta header apenas se response existir (no caso de except raise, o handler lida)
            # Mas aqui no finally, 'response' pode não estar definido se exceção ocorreu antes de call_next retornar
            # O 'try/except' acima garante que 'status_code' tem valor, mas 'response' pode não ter.
            # Como estamos fazendo raise no except, este bloco finally roda, mas não temos objeto response seguro para modificar se explodiu.
            # Para evitar UnboundLocalError, a modificação do header deve ser feita no bloco 'try' ou verificada aqui.
            pass
        
        # Adiciona headers de rastreabilidade na resposta (Se sucesso)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Execution-Time"] = f"{execution_time_ms:.2f}ms"
        
        return response
