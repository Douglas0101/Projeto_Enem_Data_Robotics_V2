from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NumericRule:
    column: str
    min_value: float | None = None
    max_value: float | None = None


@dataclass(frozen=True)
class DomainRule:
    column: str
    allowed_values: set[str]
    unknown_label: str = "UNKNOWN"


@dataclass(frozen=True)
class CleaningPlan:
    numeric_rules: tuple[NumericRule, ...]
    domain_rules: tuple[DomainRule, ...]
    dedup_keys: tuple[str, ...]


DEFAULT_NUMERIC_RULES: tuple[NumericRule, ...] = (
    NumericRule(column="NU_IDADE", min_value=8, max_value=120),
    NumericRule(column="NOTA_CIENCIAS_NATUREZA", min_value=0, max_value=1000),
    NumericRule(column="NOTA_CIENCIAS_HUMANAS", min_value=0, max_value=1000),
    NumericRule(column="NOTA_LINGUAGENS_CODIGOS", min_value=0, max_value=1000),
    NumericRule(column="NOTA_MATEMATICA", min_value=0, max_value=1000),
    NumericRule(column="NOTA_REDACAO", min_value=0, max_value=1000),
)


def build_cleaning_plan(year: int, socio_domains: dict[str, set[str]] | None = None) -> CleaningPlan:
    domain_rules: list[DomainRule] = []
    if socio_domains:
        for column, values in socio_domains.items():
            domain_rules.append(DomainRule(column=column, allowed_values=set(values)))

    plan = CleaningPlan(
        numeric_rules=DEFAULT_NUMERIC_RULES,
        domain_rules=tuple(domain_rules),
        dedup_keys=("ID_INSCRICAO", "NU_INSCRICAO", "ANO"),
    )
    return plan
