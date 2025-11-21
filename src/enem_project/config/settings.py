from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """
    Configurações centrais do projeto ENEM Data Robotics.
    """
    # .../src/enem_project/config/settings.py  → parents[3] = raiz do projeto
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = PROJECT_ROOT / "data"

    # anos cobertos pelo projeto (1998 a 2024)
    YEARS: tuple[int, ...] = tuple(range(1998, 2025))

    @property
    def years(self) -> tuple[int, ...]:
        """
        Alias em minúsculo para compatibilizar com outros módulos.
        Permite usar settings.years ou settings.YEARS.
        """
        return self.YEARS


settings = Settings()
