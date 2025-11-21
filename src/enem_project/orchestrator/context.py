from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class DatasetArtifact:
    path: Path
    row_count: int
    columns: tuple[str, ...] | None = None


@dataclass
class DataHandle:
    name: str
    sensitivity: str  # "RAW", "SENSITIVE", "AGGREGATED"
    payload: Any      # DataFrame, caminho de arquivo, etc.


@dataclass
class OrchestratorContext:
    run_id: str
    params: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, DataHandle] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)

    def add_data(self, key: str, handle: DataHandle) -> None:
        self.data[key] = handle

    def get_data(self, key: str) -> DataHandle:
        return self.data[key]

    def add_log(self, message: str) -> None:
        self.logs.append(message)

    def drop_data(self, key: str) -> None:
        handle = self.data.pop(key, None)
        if handle is not None:
            handle.payload = None
