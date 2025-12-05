from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TbNotasStatsRow(BaseModel):
    ANO: int
    TOTAL_INSCRITOS: int

    IDADE_mean: Optional[float]
    IDADE_std: Optional[float]
    IDADE_min: Optional[float]
    IDADE_median: Optional[float]
    IDADE_max: Optional[float]

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
    INSCRITOS: Optional[int] = None

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


class TbNotasGeoUfRow(BaseModel):
    ANO: int
    SG_UF_PROVA: str
    INSCRITOS: int

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


class TbNotasHistogramRow(BaseModel):
    ANO: int
    DISCIPLINA: str
    BIN_START: float
    BIN_END: float
    CONTAGEM: int


class TbSocioRaceRow(BaseModel):
    ANO: Optional[int] = None
    RACA: str
    NOTA_MATEMATICA: Optional[float]
    NOTA_CIENCIAS_NATUREZA: Optional[float]
    NOTA_CIENCIAS_HUMANAS: Optional[float]
    NOTA_LINGUAGENS_CODIGOS: Optional[float]
    NOTA_REDACAO: Optional[float]
    COUNT: int


class TbSocioIncomeRow(BaseModel):
    CLASSE: str
    LOW: float
    Q1: float
    MEDIAN: float
    Q3: float
    HIGH: float


class TbRadarRow(BaseModel):
    metric: str
    br_mean: Optional[float]
    uf_mean: Optional[float]
    best_uf_mean: Optional[float]
    full_mark: int


class HealthResponse(BaseModel):
    status: str
    detail: str


class ErrorResponse(BaseModel):
    """
    Schema padrão para retorno de erros da API.
    """

    error: str
    message: str
    request_id: Optional[str] = None
