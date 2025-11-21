from __future__ import annotations

from pathlib import Path

from .settings import settings


def raw_dir() -> Path:
    path = settings.DATA_DIR / "00_raw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def silver_dir() -> Path:
    path = settings.DATA_DIR / "01_silver"
    path.mkdir(parents=True, exist_ok=True)
    return path


def gold_dir() -> Path:
    path = settings.DATA_DIR / "02_gold"
    path.mkdir(parents=True, exist_ok=True)
    return path


def raw_data_path(year: int) -> Path:
    """
    Caminho completo para o CSV bruto do ENEM
    em data/00_raw/microdados_enem_YYYY/DADOS/MICRODADOS_ENEM_YYYY.csv
    """
    base = raw_dir() / f"microdados_enem_{year}"
    file_name = f"MICRODADOS_ENEM_{year}.csv"
    file_name_lower = file_name.lower()

    # Alguns anos usam "DADOS", outros "Dados" (case-sensitive em Linux).
    for folder in ("DADOS", "Dados", "dados"):
        candidate = base / folder / file_name
        if candidate.exists():
            return candidate

    # Fallback: busca case-insensitive pelo arquivo dentro da pasta do ano,
    # pois alguns dumps são entregues com nomes em minúsculas.
    for path in base.rglob("*.csv"):
        # Comparação casefold garante que microdados_enem_2016.csv seja aceito
        if path.name.lower() == file_name_lower:
            return path

    # Último recurso: caminho padrão (deixando FileNotFoundError ser tratado
    # por quem chamar, com logging adequado).
    return base / "DADOS" / file_name
