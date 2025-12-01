from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class ClassDefinition:
    name: str
    input_columns: tuple[str, ...]
    transformer: Callable[..., str]
    description: str = ""


def faixa_etaria(valor: int | float | None) -> str:
    if valor is None:
        return "NA"
    try:
        idade = int(valor)
    except (TypeError, ValueError):
        return "NA"
    if idade < 15:
        return "<15"
    if idade <= 17:
        return "15-17"
    if idade <= 20:
        return "18-20"
    if idade <= 25:
        return "21-25"
    if idade <= 35:
        return "26-35"
    if idade <= 50:
        return "36-50"
    return "50+"


def nota_quantil(nota: float | None) -> str:
    if nota is None:
        return "NA"
    try:
        valor = float(nota)
    except (TypeError, ValueError):
        return "NA"
    if math.isnan(valor):
        return "NA"
    if valor < 400:
        return "BAIXA"
    if valor < 600:
        return "MEDIA"
    if valor < 800:
        return "ALTA"
    return "EXCELENTE"


def renda_categoria(renda: str | None) -> str:
    if renda is None or renda is pd.NA:
        return "NA"
    try:
        renda_str = str(renda).strip().upper()
    except Exception:
        return "NA"
    mapping = {
        "A": "0-1 SM",
        "B": "1-3 SM",
        "C": "3-5 SM",
        "D": "5-10 SM",
        "E": "10+ SM",
    }
    return mapping.get(renda_str, renda_str or "NA")


def _safe_float(value: object) -> float | None:
    """
    Converte valores para float tratando corretamente valores nulos
    (None, NaN, pd.NA). Retorna None quando não for possível converter.
    """
    if value is None or value is pd.NA:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric):
        return None
    return numeric


def nota_global(linguagens: object, matematica: object) -> str:
    """
    Calcula uma nota global média a partir das notas de linguagens e
    matemática, ignorando valores ausentes e classificando via
    nota_quantil. Se ambas as notas forem nulas, retorna 'NA'.
    """
    v_linguagens = _safe_float(linguagens)
    v_matematica = _safe_float(matematica)
    valores = [v for v in (v_linguagens, v_matematica) if v is not None]
    if not valores:
        return "NA"
    media = sum(valores) / len(valores)
    return nota_quantil(media)


def build_default_definitions() -> tuple[ClassDefinition, ...]:
    return (
        ClassDefinition(
            name="CLASS_FAIXA_ETARIA",
            input_columns=("NU_IDADE",),
            transformer=lambda idade: faixa_etaria(idade),
            description="Faixas etárias padronizadas para análises demográficas.",
        ),
        ClassDefinition(
            name="CLASS_NOTA_GLOBAL",
            input_columns=("NOTA_LINGUAGENS_CODIGOS", "NOTA_MATEMATICA"),
            transformer=nota_global,
            description="Classificação por quantis aproximados das notas.",
        ),
        ClassDefinition(
            name="CLASS_RENDA_FAMILIAR",
            input_columns=("RENDA_FAMILIAR",),
            transformer=lambda renda: renda_categoria(renda),
            description="Classes socioeconômicas baseadas no questionário socioeconômico.",
        ),
    )
