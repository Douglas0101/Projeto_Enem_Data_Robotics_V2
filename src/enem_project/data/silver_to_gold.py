"""
Módulo responsável pela transformação de dados da camada Silver para Gold.

Contém funções para:
- Limpeza e normalização de colunas.
- Agregação de estatísticas (notas, distribuição geográfica, socioeconômica).
- Geração de tabelas finais em formato Parquet para consumo pelo Dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import yaml

from enem_project.config import paths
from enem_project.infra.io import read_parquet, write_parquet
from enem_project.infra.logging import logger

try:  # pragma: no cover - duckdb é opcional, mas acelera agregações grandes
    import duckdb
except ImportError:  # pragma: no cover
    duckdb = None

gold_dir = paths.gold_dir


@dataclass
class ParquetStreamingConfig:
    """Configuração para processamento em stream de arquivos Parquet."""

    rows_per_batch: int


DEFAULT_NOTA_COLUMNS = [
    "NOTA_CIENCIAS_NATUREZA",
    "NOTA_CIENCIAS_HUMANAS",
    "NOTA_LINGUAGENS_CODIGOS",
    "NOTA_MATEMATICA",
    "NOTA_REDACAO",
]

GEO_COLUMNS = ["SG_UF_PROVA", "CO_MUNICIPIO_PROVA", "NO_MUNICIPIO_PROVA"]
DEMOGRAPHIC_COLUMNS = ["TP_SEXO", "TP_COR_RACA", "TP_FAIXA_ETARIA", "NU_IDADE"]

ALIAS_MAP = {
    "NU_INSCRICAO": "ID_INSCRICAO",
    "NU_NOTA_CN": "NOTA_CIENCIAS_NATUREZA",
    "NU_NOTA_CH": "NOTA_CIENCIAS_HUMANAS",
    "NU_NOTA_LC": "NOTA_LINGUAGENS_CODIGOS",
    "NU_NOTA_MT": "NOTA_MATEMATICA",
    "NU_NOTA_REDACAO": "NOTA_REDACAO",
}


def _clean_columns(
    df: pd.DataFrame,
    year: int,
    *,
    extra_columns: list[str] | None = None,
) -> pd.DataFrame:
    rename_map = {col: ALIAS_MAP.get(col, col) for col in df.columns}
    df = df.rename(columns=rename_map)
    if "ANO" not in df.columns:
        df["ANO"] = year
    else:
        df["ANO"] = pd.to_numeric(
            df["ANO"], errors="coerce").fillna(year).astype(int)

    for col in DEFAULT_NOTA_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    if "ID_INSCRICAO" in df.columns:
        df["ID_INSCRICAO"] = df["ID_INSCRICAO"].astype(str)
    elif "NU_INSCRICAO" in df.columns:
        df["ID_INSCRICAO"] = df["NU_INSCRICAO"].astype(str)

    # Normaliza colunas geográficas quando disponíveis
    if "SG_UF_PROVA" in df.columns:
        df["SG_UF_PROVA"] = df["SG_UF_PROVA"].astype("category")
    if "CO_MUNICIPIO_PROVA" in df.columns:
        df["CO_MUNICIPIO_PROVA"] = pd.to_numeric(
            df["CO_MUNICIPIO_PROVA"], errors="coerce"
        ).astype("Int32")
    if "NO_MUNICIPIO_PROVA" in df.columns:
        df["NO_MUNICIPIO_PROVA"] = df["NO_MUNICIPIO_PROVA"].astype("string")

    # Normaliza demografia (faixa etária/sexo/raça) e idade.
    if "TP_SEXO" in df.columns:
        df["TP_SEXO"] = df["TP_SEXO"].astype("category")
    for cat_col in ("TP_COR_RACA", "TP_FAIXA_ETARIA"):
        if cat_col in df.columns:
            df[cat_col] = pd.to_numeric(
                df[cat_col], errors="coerce").astype("Int16")
        if "NU_IDADE" in df.columns:
            age_series = pd.to_numeric(df["NU_IDADE"], errors="coerce")
            valid_age = age_series.between(8, 120)
            out_of_range = int((~valid_age).sum())
            if out_of_range > 0:
                logger.warning(
                    "Ano {}: descartando {} idades fora do intervalo [8,120].",
                    year,
                    out_of_range,
                )
            df["NU_IDADE"] = age_series.where(valid_age).astype("Int16")

    extras = extra_columns or []
    desired_cols = [
        "ANO",
        "ID_INSCRICAO",
        *DEMOGRAPHIC_COLUMNS,
        *extras,
        *DEFAULT_NOTA_COLUMNS,
    ]
    present_cols: list[str] = []
    for c in desired_cols:
        if c in df.columns and c not in present_cols:
            present_cols.append(c)
    return df[present_cols]


def _cleaned_path(year: int) -> Path:
    return gold_dir() / "cleaned" / f"microdados_enem_{year}_clean.parquet"


def _stream_config() -> ParquetStreamingConfig:
    env_value = int(
        os.getenv("ENEM_PARQUET_STREAM_ROWS", "0") or 0,
    )
    if env_value > 0:
        return ParquetStreamingConfig(rows_per_batch=env_value)
    # Fallback seguro para evitar batches gigantes ou None.
    return ParquetStreamingConfig(rows_per_batch=200_000)


def build_tb_notas_parquet_streaming(years: Iterable[int]) -> int:
    """Gera tabela de notas unificada usando processamento em stream."""
    config = _stream_config()
    total_rows = 0
    tb_notas_path = gold_dir() / "tb_notas.parquet"
    tb_notas_path.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None

    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            raise FileNotFoundError(path)
        logger.info("Construindo tb_notas (streaming) a partir de {}", path)

        pf = pq.ParquetFile(path)
        batch_size = (
            config.rows_per_batch
            if config.rows_per_batch and config.rows_per_batch > 0
            else 200_000
        )
        for batch in pf.iter_batches(batch_size=batch_size):
            df_batch = batch.to_pandas()
            df_batch = _clean_columns(df_batch, year)
            total_rows += len(df_batch)

            table = pa.Table.from_pandas(df_batch, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(tb_notas_path, table.schema)
            writer.write_table(table)

    if writer is None:
        # Nenhum dado processado: cria arquivo vazio com schema esperado
        empty = pd.DataFrame(
            columns=["ANO", "ID_INSCRICAO", *
                     DEMOGRAPHIC_COLUMNS, *DEFAULT_NOTA_COLUMNS]
        )
        write_parquet(empty, tb_notas_path)
    else:
        writer.close()

    logger.info(
        "tb_notas gerado em {} com {} linhas (streaming).",
        tb_notas_path,
        total_rows,
    )
    return total_rows


def _aggregate_stats(df: pd.DataFrame) -> pd.DataFrame:
    group = df.groupby("ANO")
    stats_frames = []
    for year, frame in group:
        record = {"ANO": year}
        record["TOTAL_INSCRITOS"] = (
            frame["ID_INSCRICAO"].nunique()
            if "ID_INSCRICAO" in frame.columns
            else len(frame)
        )

        if "NU_IDADE" in frame.columns:
            age_series = pd.to_numeric(frame["NU_IDADE"], errors="coerce")
            valid_age = age_series.between(8, 120)
            out_age = int((~valid_age).sum())
            if out_age > 0:
                logger.warning(
                    "Ano {}: descartando {} idades fora do intervalo [8,120] "
                    "para estatísticas anuais.",
                    year,
                    out_age,
                )
            age_series = age_series.where(valid_age)
            age_valid = age_series.dropna()
            if age_valid.empty:
                record.update(
                    {
                        # Mantém como NaN para não sinalizar falsos positivos
                        # nos data checks.
                        "IDADE_mean": np.nan,
                        "IDADE_std": np.nan,
                        "IDADE_min": np.nan,
                        "IDADE_median": np.nan,
                        "IDADE_max": np.nan,
                    },
                )
            else:
                record.update(
                    {
                        "IDADE_mean": age_valid.mean(),
                        "IDADE_std": age_valid.std(),
                        "IDADE_min": age_valid.min(),
                        "IDADE_median": age_valid.median(),
                        "IDADE_max": age_valid.max(),
                    },
                )

        for col in DEFAULT_NOTA_COLUMNS:
            series = pd.to_numeric(frame[col], errors="coerce")

            valid = series.between(0, 1000)
            out_of_range = (~valid).sum()
            if out_of_range > 0:
                logger.warning(
                    "Ano {}, coluna {}: descartando {} valores fora do "
                    "intervalo [0,1000].",
                    year,
                    col,
                    out_of_range,
                )
            series = series.where(valid)
            series_valid = series.dropna()

            if series_valid.empty:
                record[f"{col}_count"] = 0
                record[f"{col}_mean"] = 0.0
                record[f"{col}_std"] = 0.0
                record[f"{col}_min"] = 0.0
                record[f"{col}_median"] = 0.0
                record[f"{col}_max"] = 0.0
            else:
                record[f"{col}_count"] = series_valid.count()
                record[f"{col}_mean"] = series_valid.mean()
                record[f"{col}_std"] = series_valid.std()
                record[f"{col}_min"] = series_valid.min()
                record[f"{col}_median"] = series_valid.median()
                record[f"{col}_max"] = series_valid.max()
        stats_frames.append(record)

    df_stats = pd.DataFrame(stats_frames)

    # Preenche apenas colunas de nota com 0
    # (idade permanece NaN para não gerar falsos avisos).
    nota_cols = [c for c in df_stats.columns if c.startswith("NOTA_")]
    age_cols = [c for c in df_stats.columns if c.startswith("IDADE_")]
    if nota_cols:
        df_stats[nota_cols] = df_stats[nota_cols].fillna(
            0).infer_objects(copy=False)
    if age_cols:
        df_stats[age_cols] = df_stats[age_cols].infer_objects(copy=False)

    return df_stats


def _geo_empty_schema() -> list[str]:
    return ["ANO", *GEO_COLUMNS, "INSCRITOS"] + [
        f"{n}_{suf}" for n in DEFAULT_NOTA_COLUMNS for suf in ("count", "mean")
    ]


def _geo_requires_columns(path: Path, required: list[str]) -> bool:
    pf = pq.ParquetFile(path)
    cols = set(pf.schema.names)
    return all(col in cols for col in required)


def _build_geo_duckdb(path: Path, year: int) -> pd.DataFrame:
    required = [*GEO_COLUMNS, *DEFAULT_NOTA_COLUMNS]
    if not _geo_requires_columns(path, required):
        logger.warning(
            "Colunas geográficas ou de notas ausentes para o ano {}; "
            "geo ficará vazio (schema preservado).",
            year,
        )
        return pd.DataFrame(columns=_geo_empty_schema())

    # Determine column for counting inscritos
    pf = pq.ParquetFile(path)
    cols = set(pf.schema.names)
    has_id = "ID_INSCRICAO" in cols
    inscritos_expr = "COUNT(DISTINCT ID_INSCRICAO)" if has_id else "COUNT(*)"

    # Presence Column Mapping for DuckDB
    # We check if columns exist to avoid SQL errors, defaulting to just
    # range check if missing
    presence_map = {
        "NOTA_CIENCIAS_NATUREZA": "TP_PRESENCA_CN",
        "NOTA_CIENCIAS_HUMANAS": "TP_PRESENCA_CH",
        "NOTA_LINGUAGENS_CODIGOS": "TP_PRESENCA_LC",
        "NOTA_MATEMATICA": "TP_PRESENCA_MT",
        "NOTA_REDACAO": "TP_PRESENCA_LC",  # Redacao is on Day 2 (LC)
    }

    col_selects = [f"{inscritos_expr} AS INSCRITOS"]
    for col in DEFAULT_NOTA_COLUMNS:
        pres_col = presence_map.get(col)

        # Check condition: Value in range AND
        # (Presence column doesn't exist OR Presence=1)
        # Note: In DuckDB, if column doesn't exist in file, we can't reference
        # it easily without dynamic check.
        # But we checked cols above.

        conditions = [f"{col} BETWEEN 0 AND 1000"]
        if pres_col and pres_col in cols:
            conditions.append(f"{pres_col} = 1")

        condition_str = " AND ".join(conditions)

        valid_case = f"CASE WHEN {condition_str} THEN {col} END"

        col_selects.append(
            f"SUM(CASE WHEN {condition_str} THEN 1 ELSE 0 END) AS {col}_count"
        )
        col_selects.append(f"AVG({valid_case}) AS {col}_mean")

    query = f"""
    SELECT
        COALESCE(CAST(ANO AS INT), {year}) AS ANO,
        SG_UF_PROVA,
        CO_MUNICIPIO_PROVA,
        NO_MUNICIPIO_PROVA,
        {", ".join(col_selects)}
    FROM read_parquet('{path.as_posix()}')
    WHERE SG_UF_PROVA IS NOT NULL
      AND CO_MUNICIPIO_PROVA IS NOT NULL
      AND NO_MUNICIPIO_PROVA IS NOT NULL
    GROUP BY 1,2,3,4
    """  # nosec B608
    return duckdb.sql(query).df()  # type: ignore[union-attr]


def _build_geo_uf_duckdb(path: Path, year: int) -> pd.DataFrame:
    pf = pq.ParquetFile(path)
    cols = set(pf.schema.names)
    required = {"SG_UF_PROVA", *DEFAULT_NOTA_COLUMNS}
    if not required.issubset(cols):
        logger.warning(
            "Colunas necessárias para geo_uf ausentes no ano {}; "
            "retorno vazio.",
            year,
        )
        return pd.DataFrame()

    has_id = "ID_INSCRICAO" in cols
    inscritos_expr = (
        "COUNT(DISTINCT ID_INSCRICAO)" if has_id else "COUNT(*)"
    )

    col_selects = [f"{inscritos_expr} AS INSCRITOS"]
    for col in DEFAULT_NOTA_COLUMNS:
        valid_case = f"CASE WHEN {col} BETWEEN 0 AND 1000 THEN {col} END"
        col_selects.append(
            f"SUM(CASE WHEN {col} BETWEEN 0 AND 1000 THEN 1 ELSE 0 END) "
            f"AS {col}_count"
        )
        col_selects.append(f"AVG({valid_case}) AS {col}_mean")

    query = f"""
    SELECT
        COALESCE(CAST(ANO AS INT), {year}) AS ANO,
        SG_UF_PROVA,
        {", ".join(col_selects)}
    FROM read_parquet('{path.as_posix()}')
    WHERE SG_UF_PROVA IS NOT NULL
    GROUP BY 1,2
    """  # nosec B608
    return duckdb.sql(query).df()  # type: ignore[union-attr]


def build_tb_notas_stats_from_cleaned(
    years: Iterable[int],
) -> pd.DataFrame:
    """
    Gera tabela de estatísticas anuais de notas (média, desvio, min, max).
    """
    # Calcula stats por ano lendo os Parquets limpos ano a ano
    records: list[dict[str, object]] = []
    columns_to_read = ["ID_INSCRICAO", "NU_IDADE", *DEFAULT_NOTA_COLUMNS]
    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning(
                "Arquivo limpo não encontrado para o ano {} em {}; ignorando.",
                year,
                path,
            )
            continue
        df = read_parquet(path, columns=columns_to_read)
        df = _clean_columns(df, year)
        stats_year = _aggregate_stats(df)
        records.extend(stats_year.to_dict(orient="records"))

    stats = pd.DataFrame(records)
    stats_path = gold_dir() / "tb_notas_stats.parquet"
    write_parquet(stats, stats_path)
    return stats


def build_tb_notas_geo_from_cleaned(years: Iterable[int]) -> pd.DataFrame:
    """Gera tabela de notas agregada por município."""
    frames: list[pd.DataFrame] = []
    # Include presence columns to correctly filter absentees
    # from grade averages
    columns_to_read = [
        "ID_INSCRICAO",
        *GEO_COLUMNS,
        *DEFAULT_NOTA_COLUMNS,
        "TP_PRESENCA_CN",
        "TP_PRESENCA_CH",
        "TP_PRESENCA_LC",
        "TP_PRESENCA_MT",
        "TP_STATUS_REDACAO",
    ]

    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning(
                "Arquivo limpo não encontrado para o ano {} em {}; ignorando.",
                year,
                path,
            )
            continue

        if duckdb is not None:
            try:
                frames.append(_build_geo_duckdb(path, year))
                continue
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "DuckDB falhou em geo {} ({}); caindo para pandas.",
                    year,
                    exc,
                )

        # Load data with presence columns
        try:
            df = read_parquet(path, columns=columns_to_read)
        except Exception:  # pylint: disable=broad-exception-caught
            # Fallback if presence columns are missing in older schemas
            logger.warning(
                "Colunas de presença ausentes em {}. "
                "Carregando apenas notas/geo.",
                path,
            )
            df = read_parquet(
                path, columns=[
                    c for c in columns_to_read if not c.startswith("TP_")]
            )

        df = _clean_columns(df, year, extra_columns=GEO_COLUMNS)

        if not all(col in df.columns for col in GEO_COLUMNS):
            logger.warning(
                "Colunas geográficas ausentes para o ano {}; "
                "geo ficará vazio (schema preservado).",
                year,
            )
            empty = pd.DataFrame(columns=_geo_empty_schema())
            frames.append(empty)
            continue

        # Apply Logic: Force NaN for Absentees based on Presence Columns
        # This ensures count() only counts those present, while size() counts
        # everyone (Enrolled)

        # Map Subject -> Presence Column
        presence_map = {
            "NOTA_CIENCIAS_NATUREZA": "TP_PRESENCA_CN",
            "NOTA_CIENCIAS_HUMANAS": "TP_PRESENCA_CH",
            "NOTA_LINGUAGENS_CODIGOS": "TP_PRESENCA_LC",
            "NOTA_MATEMATICA": "TP_PRESENCA_MT",
        }

        for col in DEFAULT_NOTA_COLUMNS:
            # 1. Clean numeric range first
            series = pd.to_numeric(df[col], errors="coerce")
            valid_range = series.between(0, 1000)

            # 2. Apply Presence Filter if column exists
            if col in presence_map and presence_map[col] in df.columns:
                presence_col = presence_map[col]
                # Keep value only if range is valid AND Presence == 1 (Present)
                # Note: TP_PRESENCA might be string or int, allow for both
                is_present = pd.to_numeric(
                    df[presence_col], errors="coerce") == 1
                valid = valid_range & is_present
            elif col == "NOTA_REDACAO" and "TP_STATUS_REDACAO" in df.columns:
                # For Redacao, check Status. 1 = No problems.
                # Also usually linked to LC presence, but Status is more
                # specific for the grade validity.
                # Using Presence LC as well is safer if available.
                # is_valid_status check removed as it was unused logic.

                # Actually, INEP Dict: 1=Presente(Regular), 2=Branco, 3=Nulo,
                # 4=Anulada, 6=Presente(Oral), 8=Presente(Libras).
                # Absentees usually have Status=NaN or empty in processed data
                # if not present.
                # Let's stick to the Note being Non-Null and in Range as the
                # primary check, but if TP_PRESENCA_LC is 0, Redacao should
                # be NaN.

                valid = valid_range
                if "TP_PRESENCA_LC" in df.columns:
                    is_present_lc = (
                        pd.to_numeric(df["TP_PRESENCA_LC"],
                                      errors="coerce") == 1
                    )
                    valid = valid & is_present_lc
            else:
                valid = valid_range

            df[col] = series.where(valid)

        grouped = df.groupby(
            ["ANO", "SG_UF_PROVA", "CO_MUNICIPIO_PROVA", "NO_MUNICIPIO_PROVA"],
            dropna=True,
            observed=False,
        )

        if "ID_INSCRICAO" in df.columns:
            inscritos_agg = grouped["ID_INSCRICAO"].nunique().rename(
                "INSCRITOS")
        else:
            inscritos_agg = grouped.size().rename("INSCRITOS")

        agg_parts: list[pd.Series] = [inscritos_agg]
        for col in DEFAULT_NOTA_COLUMNS:
            agg_parts.extend(
                [
                    grouped[col].count().rename(f"{col}_count"),
                    grouped[col].mean().rename(f"{col}_mean"),
                ]
            )
        geo_df_year = pd.concat(agg_parts, axis=1).reset_index()
        frames.append(geo_df_year)

    if frames:
        geo_df = pd.concat(frames, ignore_index=True)
    else:
        geo_df = pd.DataFrame(columns=_geo_empty_schema())

    geo_path = gold_dir() / "tb_notas_geo.parquet"
    write_parquet(geo_df, geo_path)
    return geo_df


def build_tb_notas_geo_uf_from_cleaned(
    years: Iterable[int],
) -> pd.DataFrame:
    """Gera tabela de notas agregada por UF."""
    frames: list[pd.DataFrame] = []
    columns_to_read = ["SG_UF_PROVA", "ID_INSCRICAO", *DEFAULT_NOTA_COLUMNS]
    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning(
                "Arquivo limpo não encontrado para o ano {} em {}; ignorando.",
                year,
                path,
            )
            continue

        if duckdb is not None:
            try:
                frames.append(_build_geo_uf_duckdb(path, year))
                continue
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "DuckDB falhou em geo_uf {} ({}); caindo para pandas.",
                    year,
                    exc,
                )

        df = read_parquet(path, columns=columns_to_read)
        df = _clean_columns(df, year, extra_columns=["SG_UF_PROVA"])

        if "SG_UF_PROVA" not in df.columns:
            logger.warning(
                "Coluna SG_UF_PROVA ausente para o ano {}; "
                "geo (UF) ficará vazio.",
                year,
            )
            continue

        for col in DEFAULT_NOTA_COLUMNS:
            series = pd.to_numeric(df[col], errors="coerce")
            valid = series.between(0, 1000)
            df[col] = series.where(valid)

        grouped = df.groupby(["ANO", "SG_UF_PROVA"],
                             dropna=True, observed=False)

        if "ID_INSCRICAO" in df.columns:
            inscritos_agg = grouped["ID_INSCRICAO"].nunique().rename(
                "INSCRITOS")
        else:
            logger.warning(
                "ID_INSCRICAO não encontrado para o ano {}. Usando o tamanho "
                "do grupo como contagem de inscritos.",
                year,
            )
            inscritos_agg = grouped.size().rename("INSCRITOS")

        agg_parts: list[pd.Series] = [inscritos_agg]
        for col in DEFAULT_NOTA_COLUMNS:
            agg_parts.extend(
                [
                    grouped[col].count().rename(f"{col}_count"),
                    grouped[col].mean().rename(f"{col}_mean"),
                ]
            )
        geo_df_year = pd.concat(agg_parts, axis=1).reset_index()
        frames.append(geo_df_year)

    if not frames:
        return pd.DataFrame()

    geo_df = pd.concat(frames, ignore_index=True)
    geo_path = gold_dir() / "tb_notas_geo_uf.parquet"
    write_parquet(geo_df, geo_path)
    logger.info("Tabela Geográfica por UF gerada em {}.", geo_path)
    return geo_df


def build_tb_notas_histogram_from_cleaned(
    years: Iterable[int],
    bins: int = 50,
    range_min: int = 0,
    range_max: int = 1000,
) -> pd.DataFrame:
    """Gera tabela de histogramas de notas."""
    all_hist_frames = []
    bin_edges = np.linspace(range_min, range_max, bins + 1)

    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning(
                "Arquivo limpo não encontrado para o ano {}; ignorando.",
                year,
                path,
            )
            continue

        df = read_parquet(path, columns=DEFAULT_NOTA_COLUMNS)
        df_year_hists = []

        for col in DEFAULT_NOTA_COLUMNS:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            valid = series.between(range_min, range_max)
            series = series[valid]

            if series.empty:
                continue

            counts, _ = np.histogram(series, bins=bin_edges)

            hist_df = pd.DataFrame(
                {
                    "ANO": year,
                    "DISCIPLINA": col,
                    "BIN_START": bin_edges[:-1],
                    "BIN_END": bin_edges[1:],
                    "CONTAGEM": counts,
                }
            )
            df_year_hists.append(hist_df)

        if df_year_hists:
            all_hist_frames.extend(df_year_hists)

    if not all_hist_frames:
        return pd.DataFrame()

    final_df = pd.concat(all_hist_frames, ignore_index=True)
    hist_path = gold_dir() / "tb_notas_histogram.parquet"
    write_parquet(final_df, hist_path)
    logger.info("Tabela de histograma gerada em {}.", hist_path)
    return final_df


Q006_MAP = {
    "A": "Sem Renda",
    "B": "Classe E (< 2 SM)",
    "C": "Classe E (< 2 SM)",
    "D": "Classe D (2-4 SM)",
    "E": "Classe D (2-4 SM)",
    "F": "Classe C (4-10 SM)",
    "G": "Classe C (4-10 SM)",
    "H": "Classe B (10-20 SM)",
    "I": "Classe B (10-20 SM)",
    "J": "Classe B (10-20 SM)",
    "K": "Classe B (10-20 SM)",
    "L": "Classe B (10-20 SM)",
    "M": "Classe A (> 20 SM)",
    "N": "Classe A (> 20 SM)",
    "O": "Classe A (> 20 SM)",
    "P": "Classe A (> 20 SM)",
    "Q": "Classe A (> 20 SM)",
}


def build_tb_socio_economico_from_cleaned(
    years: Iterable[int],
) -> pd.DataFrame:
    """
    Gera a tabela Gold de indicadores socioeconômicos (Renda x Nota),
    aplicando filtros de qualidade (presença) e mapa de classes.
    """
    frames = []
    # Colunas necessárias: Notas + Q006 + Presença
    cols = [
        "Q006",
        "TP_PRESENCA_CN",
        "TP_PRESENCA_CH",
        "TP_PRESENCA_LC",
        "TP_PRESENCA_MT",
        "TP_STATUS_REDACAO",
        *DEFAULT_NOTA_COLUMNS,
    ]

    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            continue

        # Leitura otimizada
        try:
            df = read_parquet(path, columns=cols)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Colunas socioeconômicas ausentes em {} ({}). Pulando.",
                path,
                exc,
            )
            continue

        # 1. Filtro de Qualidade
        # (Apenas quem foi em tudo e não zerou redação por falta)
        # PRESENCA = 1 (Presente), STATUS_REDACAO = 1 (Sem problemas)
        mask = (
            (df["TP_PRESENCA_CN"] == 1)
            & (df["TP_PRESENCA_CH"] == 1)
            & (df["TP_PRESENCA_LC"] == 1)
            & (df["TP_PRESENCA_MT"] == 1)
            & (df["TP_STATUS_REDACAO"] == 1)
        )
        df_valid = df[mask].copy()

        if df_valid.empty:
            continue

        # 2. Cálculo da Nota Geral (Média Simples)
        df_valid["NOTA_GERAL"] = df_valid[DEFAULT_NOTA_COLUMNS].mean(axis=1)

        # 3. Mapeamento de Classe
        df_valid["CLASSE"] = df_valid["Q006"].map(Q006_MAP)
        df_valid = df_valid.dropna(subset=["CLASSE"])

        # 4. Agregação Robusta (Percentis)
        # Agrupa por CLASSE e calcula estatísticas
        stats = (
            df_valid.groupby("CLASSE")["NOTA_GERAL"]
            .agg(
                LOW="min",
                Q1=lambda x: x.quantile(0.25),
                MEDIAN="median",
                Q3=lambda x: x.quantile(0.75),
                HIGH="max",
                COUNT="count",
            )
            .reset_index()
        )

        stats["ANO"] = year
        frames.append(stats)

    if not frames:
        return pd.DataFrame()

    final_df = pd.concat(frames, ignore_index=True)

    # Ordenação lógica das classes para o gráfico
    class_order = [
        "Classe A (> 20 SM)",
        "Classe B (10-20 SM)",
        "Classe C (4-10 SM)",
        "Classe D (2-4 SM)",
        "Classe E (< 2 SM)",
        "Sem Renda",
    ]
    final_df["CLASSE"] = pd.Categorical(
        final_df["CLASSE"], categories=class_order, ordered=True
    )
    final_df = final_df.sort_values("CLASSE")

    out_path = gold_dir() / "tb_socio_economico.parquet"
    write_parquet(final_df, out_path)
    logger.info("Tabela socioeconômica gerada em {}.", out_path)
    return final_df


# ---------------------------------------------------------------------------
# MÉDIA POR UF (5 DISCIPLINAS)
# ---------------------------------------------------------------------------

def _load_faixas_config() -> list[dict]:
    """
    Carrega a configuração de faixas de média do arquivo YAML.
    Retorna lista de dicionários com id, min, max, descricao.
    """
    config_path = paths.settings.PROJECT_ROOT / "config" / "faixas_media.yaml"
    if not config_path.exists():
        logger.warning(
            "Arquivo de configuração de faixas não encontrado em {}. "
            "Usando faixas padrão.",
            config_path,
        )
        return [
            {"id": 1, "min": 0, "max": 400, "descricao": "Abaixo de 400"},
            {
                "id": 2,
                "min": 400,
                "max": 600,
                "descricao": "Intermediário baixo",
            },
            {
                "id": 3,
                "min": 600,
                "max": 800,
                "descricao": "Intermediário alto",
            },
            {"id": 4, "min": 800, "max": 1000, "descricao": "Alto desempenho"},
        ]

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("faixas", [])


def calcular_media_5_disc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula a média das 5 disciplinas do ENEM para cada aluno.

    Exclui alunos que não possuem todas as 5 notas válidas (non-null).
    Retorna DataFrame filtrado com coluna MEDIA_5_DISC adicionada.

    Args:
        df: DataFrame com colunas de notas (DEFAULT_NOTA_COLUMNS)

    Returns:
        DataFrame com alunos válidos e coluna MEDIA_5_DISC
    """
    # Verifica quais colunas de notas estão disponíveis
    nota_cols = [c for c in DEFAULT_NOTA_COLUMNS if c in df.columns]

    if len(nota_cols) < 5:
        logger.warning(
            "Menos de 5 colunas de notas disponíveis ({}). "
            "Média será calculada com {} disciplinas.",
            nota_cols,
            len(nota_cols),
        )

    if not nota_cols:
        logger.error(
            "Nenhuma coluna de notas encontrada para cálculo da média.")
        return df

    # Converte para numérico e valida range [0, 1000]
    for col in nota_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        # Valores fora do range viram NaN
        df.loc[~df[col].between(0, 1000), col] = np.nan

    # Filtra apenas alunos com todas as notas válidas
    mask_completo = df[nota_cols].notna().all(axis=1)
    df_validos = df[mask_completo].copy()

    descartados = len(df) - len(df_validos)
    if descartados > 0:
        logger.info(
            "Media 5 disc: {} alunos descartados por notas incompletas.",
            descartados,
        )

    # Calcula a média arredondada para 2 casas decimais
    df_validos["MEDIA_5_DISC"] = (
        df_validos[nota_cols].mean(axis=1).round(2)
    )

    return df_validos


def classificar_faixa(media: float, faixas: list[dict]) -> tuple[int, str]:
    """
    Classifica uma média em uma das faixas configuradas.

    Args:
        media: Valor da média (0-1000)
        faixas: Lista de faixas carregadas do config

    Returns:
        Tupla (id_faixa, descricao_faixa)
    """
    for faixa in faixas:
        faixa_min = faixa["min"]
        faixa_max = faixa["max"]
        # Último intervalo é fechado [min, max]
        if faixa_max == 1000:
            if faixa_min <= media <= faixa_max:
                return faixa["id"], faixa["descricao"]
        else:
            # Intervalos são [min, max)
            if faixa_min <= media < faixa_max:
                return faixa["id"], faixa["descricao"]

    # Fallback para faixa 1 se não encontrar
    return 1, "Abaixo de 400"


def build_tb_media_uf_from_cleaned(years: Iterable[int]) -> pd.DataFrame:
    """
    Gera a tabela Gold de distribuição de alunos por faixa de média,
    agrupada por ano e UF.

    Pipeline:
    1. Lê arquivos cleaned do gold/cleaned/
    2. Calcula média das 5 disciplinas (MEDIA_5_DISC)
    3. Classifica em faixas configuradas
    4. Agrega por ANO, UF, FAIXA
    5. Salva em gold/tb_media_uf.parquet

    Args:
        years: Iterable de anos a processar

    Returns:
        DataFrame agregado com colunas:
        - ANO, SG_UF_PROVA, ID_FAIXA, DESCRICAO_FAIXA, QTD_ALUNOS
    """
    frames: list[pd.DataFrame] = []
    faixas = _load_faixas_config()

    columns_to_read = ["SG_UF_PROVA", *DEFAULT_NOTA_COLUMNS]

    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning(
                "Arquivo limpo não encontrado para o ano {} em {}; ignorando.",
                year,
                path,
            )
            continue

        logger.info("Processando média por UF para o ano {}...", year)

        # Lê dados limpos
        df = read_parquet(path, columns=columns_to_read)
        df = _clean_columns(df, year, extra_columns=["SG_UF_PROVA"])

        if "SG_UF_PROVA" not in df.columns:
            logger.warning(
                "Coluna SG_UF_PROVA ausente para o ano {}; ignorando.", year
            )
            continue

        # Trata UF nula como "UF_DESCONHECIDA"
        uf_nulas = df["SG_UF_PROVA"].isna().sum()
        if uf_nulas > 0:
            logger.info(
                "Ano {}: {} registros com UF nula alocados em "
                "UF_DESCONHECIDA.",
                year,
                uf_nulas,
            )
            if isinstance(df["SG_UF_PROVA"].dtype, pd.CategoricalDtype):
                if "XX" not in df["SG_UF_PROVA"].cat.categories:
                    df["SG_UF_PROVA"] = df["SG_UF_PROVA"].cat.add_categories(
                        "XX")

            df["SG_UF_PROVA"] = df["SG_UF_PROVA"].fillna("XX")

        # Calcula média das 5 disciplinas
        df_com_media = calcular_media_5_disc(df)

        if df_com_media.empty:
            logger.warning(
                "Nenhum aluno válido para cálculo de média no ano {}.", year
            )
            continue

        # Classifica em faixas
        classificacoes = df_com_media["MEDIA_5_DISC"].apply(
            lambda m: classificar_faixa(m, faixas)
        )
        df_com_media["ID_FAIXA"] = classificacoes.apply(lambda x: x[0])
        df_com_media["DESCRICAO_FAIXA"] = classificacoes.apply(lambda x: x[1])

        # Agrega por ano, uf, faixa
        agg = (
            df_com_media.groupby(
                [
                    "ANO",
                    "SG_UF_PROVA",
                    "ID_FAIXA",
                    "DESCRICAO_FAIXA",
                ],
                dropna=False,
                observed=False,
            )
            .size()
            .reset_index(name="QTD_ALUNOS")
        )

        frames.append(agg)

        logger.info(
            "Ano {}: {} alunos classificados em {} grupos UF/faixa.",
            year,
            len(df_com_media),
            len(agg),
        )

    if not frames:
        logger.warning("Nenhum dado processado para tb_media_uf.")
        return pd.DataFrame(
            columns=[
                "ANO",
                "SG_UF_PROVA",
                "ID_FAIXA",
                "DESCRICAO_FAIXA",
                "QTD_ALUNOS",
            ]
        )

    final_df = pd.concat(frames, ignore_index=True)

    # Ordena por ano, UF, faixa
    final_df = final_df.sort_values(
        ["ANO", "SG_UF_PROVA", "ID_FAIXA"]
    ).reset_index(drop=True)

    out_path = gold_dir() / "tb_media_uf.parquet"
    write_parquet(final_df, out_path)
    logger.info(
        "Tabela tb_media_uf gerada em {} com {} registros.",
        out_path,
        len(final_df),
    )

    return final_df


__all__ = [
    "build_tb_notas_parquet_streaming",
    "build_tb_notas_stats_from_cleaned",
    "build_tb_notas_geo_from_cleaned",
    "build_tb_notas_geo_uf_from_cleaned",
    "build_tb_notas_histogram_from_cleaned",
    "build_tb_socio_economico_from_cleaned",
    "build_tb_media_uf_from_cleaned",
    "calcular_media_5_disc",
    "classificar_faixa",
]
