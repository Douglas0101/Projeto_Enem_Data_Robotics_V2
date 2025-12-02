from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:  # pragma: no cover - dependencia opcional em alguns ambientes
    Instrumentator = None

from ..orchestrator.workflows.sql_backend_workflow import run_sql_backend_workflow
from ..config.settings import settings
from ..infra.logging import logger
from .dashboard_router import router as dashboard_router
from .chat_router import router as chat_router
from .schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação (startup/shutdown).
    Garante que o backend SQL (DuckDB) e suas tabelas materializadas
    estejam prontos antes de aceitar requisições.
    """
    if os.getenv("ENEM_SKIP_LIFESPAN", "").lower() in ("1", "true", "yes", "on"):
        # Usado em testes ou ambientes que já materializaram o backend.
        yield
        return

    db_path = settings.DATA_DIR / "enem.duckdb"
    force_materialize = os.getenv("ENEM_FORCE_MATERIALIZE", "").lower() in ("1", "true", "yes", "on")

    # Startup: Materializa tabelas do dashboard APENAS se necessário
    if not db_path.exists() or force_materialize:
        logger.info("Iniciando materialização do backend SQL...")
        run_sql_backend_workflow(materialize_dashboard_tables=True)
    else:
        logger.info(
            "Backend SQL encontrado em {}. Pulando materialização (use ENEM_FORCE_MATERIALIZE=1 para forçar).",
            db_path
        )

    yield
    # Shutdown: (Opcional) Fechar conexões ou liberar recursos se necessário


app = FastAPI(
    title="ENEM Data Robotics API",
    version="1.0.0",
    description=(
        "API analítica para consumo profissional dos dados do projeto "
        "ENEM Data Robotics (camadas silver/gold e tabelas de dashboard)."
    ),
    lifespan=lifespan,
)

# Permite consumo pelo dashboard (localhost:5173/4173 ou domínios externos).
# Em produção, defina VITE_API_BASE_URL para o domínio da API e, se quiser,
# restrinja allow_origins a esse domínio.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse, tags=["infra"])
def health_check() -> HealthResponse:
    """
    Endpoint simples de health check para monitoramento.
    """
    return HealthResponse(status="ok", detail="ENEM Data Robotics API operational")


app.include_router(dashboard_router)
app.include_router(chat_router)

# Instrumentação de métricas Prometheus (Observabilidade)
if Instrumentator:
    Instrumentator().instrument(app).expose(app)
else:  # pragma: no cover - fallback silencioso
    import logging
    logging.getLogger(__name__).warning(
        "prometheus_fastapi_instrumentator não instalado; métricas desabilitadas."
    )
