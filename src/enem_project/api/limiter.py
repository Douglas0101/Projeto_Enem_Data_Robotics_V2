import logging
from typing import Callable

logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    # Instância global do Limiter.
    # Utiliza o endereço remoto (IP) como chave para rate limiting.
    # Em produção Enterprise, recomenda-se usar Redis como backend de armazenamento (storage_uri).
    limiter = Limiter(key_func=get_remote_address)
    logger.info("SlowAPI Limiter initialized successfully.")

except ImportError:
    logger.warning(
        "SlowAPI not found. Rate limiting will be DISABLED. Install 'slowapi' to enable."
    )

    # Fallback / Shim class to prevent import errors in routers
    class MockLimiter:
        def limit(self, limit_value: str) -> Callable:
            def decorator(func: Callable) -> Callable:
                # Just return the function unmodified
                return func

            return decorator

    limiter = MockLimiter()
