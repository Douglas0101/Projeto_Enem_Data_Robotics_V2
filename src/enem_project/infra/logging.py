from __future__ import annotations

import sys

from loguru import logger as _logger

from enem_project.config.settings import settings

# Remove handler padrão para evitar logs duplicados
_logger.remove()

# Configurações de logging baseadas no ambiente
if settings.ENVIRONMENT == "production":
    # Em produção, loga em JSON para facilitar parse por sistemas de monitoramento
    _logger.add(
        sys.stdout,
        level="INFO",
        serialize=True,  # Habilita o formato JSON
        diagnose=False,  # Não mostrar variáveis locais em caso de exceção em produção
        backtrace=True,  # Mostrar backtrace completo
        colorize=False,  # Sem cores em logs JSON
    )
    # Adicionar um handler para erros críticos em stderr, em JSON também.
    _logger.add(
        sys.stderr,
        level="ERROR",
        serialize=True,
        diagnose=False,
        backtrace=True,
        colorize=False,
    )
    _logger.info("Configurando logging em modo JSON para produção.")
else:
    # Em desenvolvimento, loga em formato legível no console
    _logger.add(
        sys.stdout,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
        diagnose=True,  # Mostrar variáveis locais em caso de exceção em desenvolvimento
        backtrace=True,
    )
    _logger.info(
        "Configurando logging em modo de console legível para desenvolvimento."
    )

logger = _logger
