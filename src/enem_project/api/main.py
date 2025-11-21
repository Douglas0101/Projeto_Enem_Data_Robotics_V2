from __future__ import annotations

from fastapi import FastAPI

from ..orchestrator.workflows.sql_backend_workflow import init_sql_backend
from .dashboard_router import router as dashboard_router
from .schemas import HealthResponse


app = FastAPI(
    title="ENEM Data Robotics API",
    version="1.0.0",
    description=(
        "API analítica para consumo profissional dos dados do projeto "
        "ENEM Data Robotics (camadas silver/gold e tabelas de dashboard)."
    ),
)


@app.on_event("startup")
def _startup_sql_backend() -> None:
    """
    Na inicialização da API, garante que o backend SQL esteja pronto.
    Isso inclui a criação/atualização do arquivo DuckDB e a
    materialização das tabelas de dashboard (tb_notas, tb_notas_stats,
    tb_notas_geo).
    """
    # Materializa tabelas para evitar que o serviço dependa da forma como
    # o CLI foi executado anteriormente.
    init_sql_backend(materialize_dashboard_tables=True)


@app.get("/health", response_model=HealthResponse, tags=["infra"])
def health_check() -> HealthResponse:
    """
    Endpoint simples de health check para monitoramento.
    """
    return HealthResponse(status="ok", detail="ENEM Data Robotics API operational")


app.include_router(dashboard_router)

