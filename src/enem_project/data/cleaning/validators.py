from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from .rules import NumericRule, DomainRule


@dataclass
class ValidationReport:
    rule_type: str
    column: str
    issue: str
    affected_rows: int

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_type": self.rule_type,
            "column": self.column,
            "issue": self.issue,
            "affected_rows": self.affected_rows,
        }


def enforce_numeric_rules(
    df: pd.DataFrame, rules: Sequence[NumericRule]
) -> tuple[pd.DataFrame, list[ValidationReport], pd.DataFrame]:
    reports: list[ValidationReport] = []
    invalid_rows: list[pd.DataFrame] = []

    cleaned = df.copy()
    for rule in rules:
        if rule.column not in cleaned.columns:
            continue

        mask = pd.Series(False, index=cleaned.index)
        if rule.min_value is not None:
            mask |= cleaned[rule.column] < rule.min_value
        if rule.max_value is not None:
            mask |= cleaned[rule.column] > rule.max_value

        violated = cleaned[mask]
        if not violated.empty:
            invalid_rows.append(violated.assign(_reason=f"range_{rule.column}"))
            reports.append(
                ValidationReport(
                    rule_type="numeric_range",
                    column=rule.column,
                    issue=f"Valores fora do range ({rule.min_value}, {rule.max_value})",
                    affected_rows=len(violated),
                )
            )
            cleaned = cleaned[~mask]
    invalid = (
        pd.concat(invalid_rows, ignore_index=True) if invalid_rows else pd.DataFrame()
    )
    return cleaned, reports, invalid


def enforce_domain_rules(
    df: pd.DataFrame, rules: Sequence[DomainRule]
) -> tuple[pd.DataFrame, list[ValidationReport]]:
    cleaned = df.copy()
    reports: list[ValidationReport] = []
    for rule in rules:
        if rule.column not in cleaned.columns:
            continue
        mask = ~cleaned[rule.column].isin(rule.allowed_values)
        affected = mask.sum()
        if affected:
            cleaned.loc[mask, rule.column] = rule.unknown_label
            reports.append(
                ValidationReport(
                    rule_type="domain",
                    column=rule.column,
                    issue=f"Valores fora do domínio {sorted(rule.allowed_values)[:10]}",
                    affected_rows=int(affected),
                )
            )
    return cleaned, reports


def drop_duplicates(
    df: pd.DataFrame, keys: Sequence[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    available_keys = [k for k in keys if k in df.columns]
    if not available_keys:
        return df, pd.DataFrame()
    duplicated_mask = df.duplicated(subset=available_keys, keep="first")
    duplicates = df[duplicated_mask].copy()
    cleaned = df[~duplicated_mask].copy()
    return cleaned, duplicates
