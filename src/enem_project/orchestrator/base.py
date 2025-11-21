from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

from .context import OrchestratorContext

if TYPE_CHECKING:
    from .security import SecurityManager


class Agent(ABC):
    name: str = "agent-base"
    allowed_sensitivity_read: List[str] = ["AGGREGATED", "SENSITIVE", "RAW"]
    allowed_sensitivity_write: List[str] = ["AGGREGATED", "SENSITIVE", "RAW"]

    @abstractmethod
    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        ...


class Orchestrator:
    def __init__(self, agents: list[Agent], security_manager: "SecurityManager"):
        self.agents = agents
        self.security_manager = security_manager

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        for agent in self.agents:
            self.security_manager.check_agent_permissions(agent, ctx)
            ctx = agent.run(ctx)
        return ctx
