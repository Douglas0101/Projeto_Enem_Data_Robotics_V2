from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TbNotasStatsRow(BaseModel):
    ANO: int

    NOTA_CIENCIAS_NATUREZA_count: int
    NOTA_CIENCIAS_NATUREZA_mean: Optional[float]
    NOTA_CIENCIAS_NATUREZA_std: Optional[float]
    NOTA_CIENCIAS_NATUREZA_min: Optional[float]
    NOTA_CIENCIAS_NATUREZA_median: Optional[float]
    NOTA_CIENCIAS_NATUREZA_max: Optional[float]

    NOTA_CIENCIAS_HUMANAS_count: int
    NOTA_CIENCIAS_HUMANAS_mean: Optional[float]
    NOTA_CIENCIAS_HUMANAS_std: Optional[float]
    NOTA_CIENCIAS_HUMANAS_min: Optional[float]
    NOTA_CIENCIAS_HUMANAS_median: Optional[float]
    NOTA_CIENCIAS_HUMANAS_max: Optional[float]

    NOTA_LINGUAGENS_CODIGOS_count: int
    NOTA_LINGUAGENS_CODIGOS_mean: Optional[float]
    NOTA_LINGUAGENS_CODIGOS_std: Optional[float]
    NOTA_LINGUAGENS_CODIGOS_min: Optional[float]
    NOTA_LINGUAGENS_CODIGOS_median: Optional[float]
    NOTA_LINGUAGENS_CODIGOS_max: Optional[float]

    NOTA_MATEMATICA_count: int
    NOTA_MATEMATICA_mean: Optional[float]
    NOTA_MATEMATICA_std: Optional[float]
    NOTA_MATEMATICA_min: Optional[float]
    NOTA_MATEMATICA_median: Optional[float]
    NOTA_MATEMATICA_max: Optional[float]

    NOTA_REDACAO_count: int
    NOTA_REDACAO_mean: Optional[float]
    NOTA_REDACAO_std: Optional[float]
    NOTA_REDACAO_min: Optional[float]
    NOTA_REDACAO_median: Optional[float]
    NOTA_REDACAO_max: Optional[float]


class TbNotasGeoRow(BaseModel):
    ANO: int
    SG_UF_PROVA: str
    CO_MUNICIPIO_PROVA: str
    NO_MUNICIPIO_PROVA: str

    NOTA_CIENCIAS_NATUREZA_count: int
    NOTA_CIENCIAS_NATUREZA_mean: Optional[float]
    NOTA_CIENCIAS_HUMANAS_count: int
    NOTA_CIENCIAS_HUMANAS_mean: Optional[float]
    NOTA_LINGUAGENS_CODIGOS_count: int
    NOTA_LINGUAGENS_CODIGOS_mean: Optional[float]
    NOTA_MATEMATICA_count: int
    NOTA_MATEMATICA_mean: Optional[float]
    NOTA_REDACAO_count: int
    NOTA_REDACAO_mean: Optional[float]


class HealthResponse(BaseModel):
    status: str
    detail: str

