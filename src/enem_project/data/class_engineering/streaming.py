from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from enem_project.data.class_engineering import transformers as class_transformers
from enem_project.infra.io import write_parquet


@dataclass
class StreamingClassResult:
    classes_path: Path
    row_count: int
    columns: tuple[str, ...]
    summary_df: pd.DataFrame


def stream_class_pipeline(
    clean_path: Path,
    classes_path: Path,
    *,
    chunk_rows: int = 50_000,
) -> StreamingClassResult:
    """
    Executa a engenharia de classes em modo streaming, lendo o Parquet limpo em
    batches e escrevendo o resultado incrementalmente para reduzir uso de RAM.
    """
    batch_size = max(1, int(chunk_rows))
    classes_path.parent.mkdir(parents=True, exist_ok=True)

    pf = pq.ParquetFile(clean_path)
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    columns: tuple[str, ...] = ()
    summary_counts: dict[tuple[str, str], int] = defaultdict(int)

    definitions = [
        class_transformers._class_faixa_etaria,
        class_transformers._class_nota_global,
        class_transformers._class_renda,
    ]
    class_columns = ["CLASS_FAIXA_ETARIA", "CLASS_NOTA_GLOBAL", "CLASS_RENDA_FAMILIAR"]

    for batch in pf.iter_batches(batch_size=batch_size):
        df_chunk = batch.to_pandas()
        transformed = class_transformers.apply_class_definitions(df_chunk, definitions)

        for col in class_columns:
            counts = transformed[col].value_counts(dropna=False)
            for value, count in counts.items():
                summary_counts[(col, str(value))] += int(count)

        table = pa.Table.from_pandas(transformed, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(classes_path, table.schema, compression="snappy")
            columns = tuple(transformed.columns)
        writer.write_table(table)
        total_rows += len(transformed)

    if writer is None:
        empty_df = pd.DataFrame(columns=pf.schema.names)
        write_parquet(empty_df, classes_path)
        columns = tuple(empty_df.columns)
    else:
        writer.close()

    summary_records = [
        {"class_name": class_name, "class_value": class_value, "total": total}
        for (class_name, class_value), total in summary_counts.items()
    ]
    summary_df = pd.DataFrame(summary_records)

    return StreamingClassResult(
        classes_path=classes_path,
        row_count=total_rows,
        columns=columns,
        summary_df=summary_df,
    )


__all__ = ["stream_class_pipeline", "StreamingClassResult"]
