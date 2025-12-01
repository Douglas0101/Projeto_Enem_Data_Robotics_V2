from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from enem_project.data.cleaning.pipeline import (
    _apply_domains,
    _validate_numeric_ranges,
)
from enem_project.data.metadata import filter_metadata_for_year, load_metadata
from enem_project.infra.io import write_parquet


@dataclass
class StreamingCleaningResult:
    cleaned_path: Path
    row_count: int
    columns: tuple[str, ...]
    cleaning_report: pd.DataFrame
    invalid_rows: pd.DataFrame
    duplicates: pd.DataFrame


def stream_clean_to_parquet(
    silver_path: Path,
    clean_path: Path,
    year: int,
    *,
    chunk_rows: int = 100_000,
    metadata: pd.DataFrame | None = None,
) -> StreamingCleaningResult:
    """
    Executa o pipeline de limpeza em modo streaming, lendo o Parquet em batches
    e persistindo incrementalmente para evitar o carregamento de todo o dataset
    na memória.
    """
    batch_size = max(1, int(chunk_rows))
    clean_path.parent.mkdir(parents=True, exist_ok=True)

    if metadata is None:
        try:
            metadata = load_metadata()
        except FileNotFoundError:
            metadata = pd.DataFrame()
    metadata_year = filter_metadata_for_year(metadata, year) if metadata is not None else pd.DataFrame()

    pf = pq.ParquetFile(silver_path)
    writer: pq.ParquetWriter | None = None
    seen_ids: set[str] = set()
    invalid_parts: list[pd.DataFrame] = []
    duplicate_parts: list[pd.DataFrame] = []
    report_counter: dict[str, int] = defaultdict(int)
    total_rows = 0
    columns: tuple[str, ...] = ()

    for batch in pf.iter_batches(batch_size=batch_size):
        df_chunk = batch.to_pandas()

        invalid_mask = _validate_numeric_ranges(df_chunk)
        invalid_rows = df_chunk[invalid_mask].copy()
        valid_chunk = df_chunk[~invalid_mask].copy()

        duplicates = pd.DataFrame()
        if "ID_INSCRICAO" in valid_chunk.columns:
            id_series = valid_chunk["ID_INSCRICAO"].astype(str)
            dup_in_chunk = id_series.duplicated(keep="first")
            dup_seen_before = id_series.isin(seen_ids)
            duplicate_mask = dup_in_chunk | dup_seen_before
            duplicates = valid_chunk[duplicate_mask].copy()
            keep_mask = ~duplicate_mask
            valid_chunk = valid_chunk[keep_mask]
            seen_ids.update(id_series[keep_mask])

        corrected_chunk, domain_report = _apply_domains(valid_chunk, metadata_year)

        if not invalid_rows.empty:
            invalid_parts.append(invalid_rows.reset_index(drop=True))
            report_counter["invalid_rows"] += len(invalid_rows)
        if not duplicates.empty:
            duplicate_parts.append(duplicates.reset_index(drop=True))
            report_counter["duplicates"] += len(duplicates)
        if not domain_report.empty:
            for _, row in domain_report.iterrows():
                rule = f"domain:{row['column']}"
                report_counter[rule] += int(row["affected_rows"])

        corrected_chunk = corrected_chunk.reset_index(drop=True)
        if writer is None:
            table = pa.Table.from_pandas(corrected_chunk, preserve_index=False)
            writer = pq.ParquetWriter(clean_path, table.schema, compression="snappy")
            columns = tuple(corrected_chunk.columns)
        else:
            table = pa.Table.from_pandas(corrected_chunk, preserve_index=False)
        writer.write_table(table)
        total_rows += len(corrected_chunk)

    if writer is None:
        # Dataset vazio ou totalmente filtrado: persiste arquivo vazio para manter contrato.
        empty_df = pd.DataFrame(columns=pf.schema.names)
        write_parquet(empty_df, clean_path)
        columns = tuple(empty_df.columns)
    else:
        writer.close()

    invalid_rows_df = pd.concat(invalid_parts, ignore_index=True) if invalid_parts else pd.DataFrame()
    duplicates_df = pd.concat(duplicate_parts, ignore_index=True) if duplicate_parts else pd.DataFrame()

    report_records: list[dict[str, int | str]] = []
    if report_counter.get("invalid_rows"):
        report_records.append({"rule": "invalid_rows", "affected_rows": report_counter["invalid_rows"]})
    if report_counter.get("duplicates"):
        report_records.append({"rule": "duplicates", "affected_rows": report_counter["duplicates"]})
    for rule, count in sorted(report_counter.items()):
        if rule in {"invalid_rows", "duplicates"}:
            continue
        report_records.append({"rule": rule, "affected_rows": count})
    cleaning_report = pd.DataFrame(report_records)

    return StreamingCleaningResult(
        cleaned_path=clean_path,
        row_count=total_rows,
        columns=columns,
        cleaning_report=cleaning_report,
        invalid_rows=invalid_rows_df,
        duplicates=duplicates_df,
    )


__all__ = ["stream_clean_to_parquet", "StreamingCleaningResult"]
