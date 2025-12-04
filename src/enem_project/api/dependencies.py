from typing import Generator
from .infra.db_agent import DuckDBAgent

def get_db_agent() -> Generator[DuckDBAgent, None, None]:
    """
    Dependency provider for DuckDBAgent.
    Ensures proper resource management in the FastAPI dependency lifecycle.
    """
    # Create an agent in read-only mode for dashboard/API usage.
    agent = DuckDBAgent(read_only=True)
    try:
        yield agent
    finally:
        # Although DuckDBAgent currently relies on internal connection pooling/checking,
        # calling close() ensures we release resources if the implementation changes
        # to use dedicated connections per request in the future.
        agent.close()