# src/enem_project/orchestrator/security.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .context import OrchestratorContext, DataHandle
from .base import Agent


class SecurityException(Exception):
    pass


@dataclass
class SecurityManager:
    policies: Dict[str, Any] | None = None

    def check_agent_permissions(self, agent: Agent, ctx: OrchestratorContext) -> None:
        for key, handle in ctx.data.items():
            if handle.sensitivity not in agent.allowed_sensitivity_read:
                ctx.add_log(
                    f"[SECURITY] Agent {agent.name} não tem permissão para ler "
                    f"{key} (sensitivity={handle.sensitivity})."
                )

    def sanitize_output(self, handle: DataHandle) -> DataHandle:
        return handle
