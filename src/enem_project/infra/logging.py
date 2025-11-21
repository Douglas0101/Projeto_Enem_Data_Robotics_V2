from __future__ import annotations

import sys

from loguru import logger as _logger

# Remove handler padrão para evitar logs duplicados
_logger.remove()

# Handler principal: console
_logger.add(
    sys.stdout,
    level="INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
)

logger = _logger
