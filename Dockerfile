# ==============================================================================
# Stage 1: Builder
# Responsável por compilar dependências e preparar o ambiente virtual.
# ==============================================================================
FROM python:3.13-slim as builder

# Variáveis de ambiente para Python e Poetry
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# Instalação de dependências de sistema necessárias para build (GCC, Make, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalação do Poetry via script oficial
RUN curl -sSL https://install.python-poetry.org | python3 - 
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

# Copia arquivos de definição de dependência PRIMEIRO para otimizar cache de camadas do Docker
COPY pyproject.toml poetry.lock ./

# Instala dependências Python no .venv local (--no-root evita instalar o próprio projeto neste estágio)
RUN poetry install --no-root --only main

# ==============================================================================
# Stage: Test
# Estágio para execução de testes automatizados e CI
# ==============================================================================
FROM builder as test

# Instala libs de sistema necessárias para o WeasyPrint (PDF) e testes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Instala todas as dependências (main + dev + test)
RUN poetry install --no-root --with dev,test

# Variáveis de ambiente para teste
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    ENEM_DATA_DIR="/tmp/test_data" \
    XDG_CACHE_HOME="/app/.cache"

# Prepara diretórios
RUN mkdir -p /tmp/test_data /app/.cache

# Copia código e testes
COPY src /app/src
COPY tests /app/tests

CMD ["pytest", "-v"]

# ==============================================================================
# Stage 2: Runtime
# Imagem final enxuta, segura e otimizada para produção.
# ==============================================================================
FROM python:3.13-slim as runtime

# Segurança: Criação de usuário não-root (appuser UID 1000)
# Rodar como root é uma vulnerabilidade crítica em containers.
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Instala apenas curl para o Healthcheck (sem build tools)
# ADICIONADO: libs para WeasyPrint (PDF) - libpango, libcairo
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Configura o PYTHONPATH para garantir que 'src' seja importável
    PYTHONPATH="/app/src" \
    # Diretório para persistência de dados mapeado no volume
    ENEM_DATA_DIR="/app/data"

WORKDIR /app

# Cria diretório de dados e ajusta permissões para o appuser
RUN mkdir -p /app/data /app/.cache && chown -R appuser:appuser /app/data /app/.cache

# Otimização: Copia apenas o ambiente virtual preparado no estágio builder
COPY --from=builder /app/.venv /app/.venv

# Copia o código fonte da aplicação
COPY src /app/src

# Segurança: Ajusta propriedade dos arquivos da aplicação
RUN chown -R appuser:appuser /app

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Configura o PYTHONPATH para garantir que 'src' seja importável
    PYTHONPATH="/app/src" \
    # Diretório para persistência de dados mapeado no volume
    ENEM_DATA_DIR="/app/data" \
    # Fix para Fontconfig (WeasyPrint) em container non-root
    XDG_CACHE_HOME="/app/.cache"

# Define o usuário não-privilegiado para execução
USER appuser

# Documenta a porta exposta
EXPOSE 8000

# Healthcheck Nativo: Garante que o orquestrador saiba se a API está saudável
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint de Produção:
# - Uvicorn como servidor ASGI
# - --workers 4 para concorrência (ajustado para limites típicos de container)
# - --proxy-headers para confiar em headers X-Forwarded-* (útil atrás de Nginx/Traefik)
# - --host 0.0.0.0 para aceitar conexões externas ao container
CMD ["uvicorn", "enem_project.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]