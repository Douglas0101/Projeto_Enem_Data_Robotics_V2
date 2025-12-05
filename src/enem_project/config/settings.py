from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Carrega variáveis do arquivo .env na raiz do projeto
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """
    Configurações centrais do projeto ENEM Data Robotics.
    """

    # .../src/enem_project/config/settings.py  → parents[3] = raiz do projeto
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = PROJECT_ROOT / "data"

    # Chaves de API e Configurações de IA
    GOOGLE_API_KEY: str | None = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY")
    )
    GEMINI_MODEL_NAME: str = "gemini-2.0-flash"  # Modelo rápido e eficiente para SQL
    ENVIRONMENT: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )

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
