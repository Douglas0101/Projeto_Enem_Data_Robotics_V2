from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:
    Instrumentator = None

from ..orchestrator.workflows.sql_backend_workflow import run_sql_backend_workflow
from ..config.settings import settings
from ..infra.logging import logger
from .dashboard_router import router as dashboard_router
from .chat_router import router as chat_router
from .schemas import HealthResponse, ErrorResponse
from .middlewares import RequestIDMiddleware

# --- Rate Limiting Imports ---
from .limiter import limiter
try:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    logger.warning("SlowAPI not installed. Rate limiting middleware will NOT be active.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação (startup/shutdown).
    """
    if os.getenv("ENEM_SKIP_LIFESPAN", "").lower() in ("1", "true", "yes", "on"):
        yield
        return

    db_path = settings.DATA_DIR / "enem.duckdb"
    force_materialize = os.getenv("ENEM_FORCE_MATERIALIZE", "").lower() in ("1", "true", "yes", "on")

    if not db_path.exists() or force_materialize:
        logger.info("Iniciando materialização do backend SQL...")
        # Note: run_sql_backend_workflow uses DuckDBAgent internally, 
        # which is synchronous. We run it as is during startup (blocking is okay here).
        run_sql_backend_workflow(materialize_dashboard_tables=True)
    else:
        logger.info(f"Backend SQL encontrado em {db_path}. Pulando materialização.")

    yield


app = FastAPI(
    title="ENEM Data Robotics API",
    version="1.0.0",
    description="API analítica profissional refatorada para estabilidade e performance.",
    lifespan=lifespan,
)

# --- Rate Limiting Setup ---
app.state.limiter = limiter
if SLOWAPI_AVAILABLE:
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

# --- Middlewares ---

app.add_middleware(RequestIDMiddleware)

# Security: Load allowed origins from env, default to safe localhost
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Exception Handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled error processing request {request_id}: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred.",
            request_id=request_id
        ).model_dump()
    )

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/health", response_model=HealthResponse, tags=["infra"])
@limiter.limit("100/minute")
def health_check(request: Request) -> HealthResponse:
    return HealthResponse(status="ok", detail="Operational")

app.include_router(dashboard_router)
app.include_router(chat_router)

if Instrumentator:
    Instrumentator().instrument(app).expose(app)