from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

import pandas as pd

from ..metadata import load_metadata


@dataclass(frozen=True)
class ColumnContract:
    nome_padrao: str
    tipo_padrao: str
    dominio_valores: list[str] | None


def _normalize_tipo(tipo: str) -> str:
    tipo = (tipo or "").lower()
    if tipo in {"int", "int64", "int32"}:
        return "int"
    if tipo in {"float", "float32", "float64"}:
        return "float"
    if tipo in {"bool", "boolean"}:
        return "bool"
    if tipo in {"datetime", "timestamp"}:
        return "datetime"
    return "string"


def build_contract_for_year(year: int, metadata: pd.DataFrame | None = None) -> dict[str, ColumnContract]:
    """
    Constrói um contrato de schema (nome->tipo/domínio) com base no metadata.
    """
    df = metadata if metadata is not None else load_metadata()
    if df.empty:
        return {}

    subset = df[df["ano"] == int(year)]
    contracts: dict[str, ColumnContract] = {}
    for _, row in subset.iterrows():
        nome = str(row["nome_padrao"])
        if not nome:
            continue
        contrato = ColumnContract(
            nome_padrao=nome,
            tipo_padrao=_normalize_tipo(str(row["tipo_padrao"])),
            dominio_valores=row["dominio_valores"] if isinstance(row["dominio_valores"], list) else None,
        )
        contracts[nome] = contrato
    return contracts


def select_known_columns(df: pd.DataFrame, contract: Mapping[str, ColumnContract]) -> pd.DataFrame:
    """
    Mantém apenas colunas presentes no contrato, preservando ordem original.
    """
    keep = [col for col in df.columns if col in contract]
    if not keep:
        return df
    return df[keep]


def infer_dtype_map(contract: Mapping[str, ColumnContract]) -> dict[str, Any]:
    dtype_map: dict[str, Any] = {}
    for name, spec in contract.items():
        if spec.tipo_padrao == "int":
            dtype_map[name] = "Int64"
        elif spec.tipo_padrao == "float":
            dtype_map[name] = "Float64"
        elif spec.tipo_padrao == "bool":
            dtype_map[name] = "boolean"
    return dtype_map
