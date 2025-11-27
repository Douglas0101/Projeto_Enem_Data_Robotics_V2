from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from enem_project.config import paths
from enem_project.infra.io import read_parquet, write_parquet
from enem_project.infra.logging import logger

gold_dir = paths.gold_dir


@dataclass
class ParquetStreamingConfig:
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
        df["ANO"] = pd.to_numeric(df["ANO"], errors="coerce").fillna(year).astype(int)

    for col in DEFAULT_NOTA_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    if "ID_INSCRICAO" in df.columns:
        df["ID_INSCRICAO"] = df["ID_INSCRICAO"].astype(str)
    elif "NU_INSCRICAO" in df.columns:
        df["ID_INSCRICAO"] = df["NU_INSCRICAO"].astype(str)

    # Normaliza colunas geográficas quando disponíveis
    if "SG_UF_PROVA" in df.columns:
        df["SG_UF_PROVA"] = df["SG_UF_PROVA"].astype(str).str.upper()
    if "CO_MUNICIPIO_PROVA" in df.columns:
        df["CO_MUNICIPIO_PROVA"] = df["CO_MUNICIPIO_PROVA"].astype(str)
    if "NO_MUNICIPIO_PROVA" in df.columns:
        df["NO_MUNICIPIO_PROVA"] = df["NO_MUNICIPIO_PROVA"].astype(str)

    # Normaliza demografia (faixa etária/sexo/raça) e idade.
    if "TP_SEXO" in df.columns:
        df["TP_SEXO"] = df["TP_SEXO"].astype("string").str.upper()
    for cat_col in ("TP_COR_RACA", "TP_FAIXA_ETARIA"):
        if cat_col in df.columns:
            df[cat_col] = pd.to_numeric(df[cat_col], errors="coerce").astype("Int64")
    if "NU_IDADE" in df.columns:
        age_series = pd.to_numeric(df["NU_IDADE"], errors="coerce")
        valid_age = age_series.between(8, 120)
        out_of_range = int((~valid_age).sum())
        if out_of_range > 0:
            logger.warning(
                "Ano %s: descartando %d idades fora do intervalo [8,120].",
                year,
                out_of_range,
            )
        df["NU_IDADE"] = age_series.where(valid_age)

    extras = extra_columns or []
    desired_cols = ["ANO", "ID_INSCRICAO", *DEMOGRAPHIC_COLUMNS, *extras, *DEFAULT_NOTA_COLUMNS]
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
    config = _stream_config()
    total_rows = 0
    tb_notas_path = gold_dir() / "tb_notas.parquet"
    tb_notas_path.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None

    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            raise FileNotFoundError(path)
        logger.info("Construindo tb_notas (streaming) a partir de %s", path)

        pf = pq.ParquetFile(path)
        batch_size = config.rows_per_batch if config.rows_per_batch and config.rows_per_batch > 0 else 200_000
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
        empty = pd.DataFrame(columns=["ANO", "ID_INSCRICAO", *DEMOGRAPHIC_COLUMNS, *DEFAULT_NOTA_COLUMNS])
        write_parquet(empty, tb_notas_path)
    else:
        writer.close()

    logger.info("tb_notas gerado em %s com %d linhas (streaming).", tb_notas_path, total_rows)
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
                    "Ano %s: descartando %d idades fora do intervalo [8,120] para estatísticas anuais.",
                    year,
                    out_age,
                )
            age_series = age_series.where(valid_age)
            record.update(
                {
                    "IDADE_mean": age_series.mean(),
                    "IDADE_std": age_series.std(),
                    "IDADE_min": age_series.min(),
                    "IDADE_median": age_series.median(),
                    "IDADE_max": age_series.max(),
                },
            )

        for col in DEFAULT_NOTA_COLUMNS:
            series = pd.to_numeric(frame[col], errors="coerce")

            valid = series.between(0, 1000)
            out_of_range = (~valid).sum()
            if out_of_range > 0:
                logger.warning(
                    "Ano %s, coluna %s: descartando %d valores fora do intervalo [0,1000].",
                    year,
                    col,
                    out_of_range,
                )
            series = series.where(valid)

            record[f"{col}_count"] = series.count()
            record[f"{col}_mean"] = series.mean()
            record[f"{col}_std"] = series.std()
            record[f"{col}_min"] = series.min()
            record[f"{col}_median"] = series.median()
            record[f"{col}_max"] = series.max()
        stats_frames.append(record)

    df_stats = pd.DataFrame(stats_frames)

    # Preenche NaNs restantes (de agregações em séries vazias) com 0.
    fill_cols = [c for c in df_stats.columns if "NOTA_" in c or "IDADE_" in c]
    df_stats[fill_cols] = df_stats[fill_cols].fillna(0)

    return df_stats


def build_tb_notas_stats_from_cleaned(years: Iterable[int]) -> pd.DataFrame:
    # Calcula stats por ano lendo os Parquets limpos ano a ano
    records: list[dict[str, object]] = []
    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning("Arquivo limpo não encontrado para o ano %s em %s; ignorando.", year, path)
            continue
        df = read_parquet(path)
        df = _clean_columns(df, year)
        stats_year = _aggregate_stats(df)
        records.extend(stats_year.to_dict(orient="records"))

    stats = pd.DataFrame(records)
    stats_path = gold_dir() / "tb_notas_stats.parquet"
    write_parquet(stats, stats_path)
    return stats


def build_tb_notas_geo_from_cleaned(years: Iterable[int]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning("Arquivo limpo não encontrado para o ano %s em %s; ignorando.", year, path)
            continue

        df = read_parquet(path)
        df = _clean_columns(df, year, extra_columns=GEO_COLUMNS)

        # Se faltar colunas geográficas, cria schema vazio para evitar quebra.
        if not all(col in df.columns for col in GEO_COLUMNS):
            logger.warning(
                "Colunas geográficas ausentes para o ano %s; geo ficará vazio (schema preservado).",
                year,
            )
            empty = pd.DataFrame(
                columns=["ANO", *GEO_COLUMNS]
                + [f"{n}_{suf}" for n in DEFAULT_NOTA_COLUMNS for suf in ("count", "mean")]
            )
            frames.append(empty)
            continue

        for col in DEFAULT_NOTA_COLUMNS:
            series = pd.to_numeric(df[col], errors="coerce")
            valid = series.between(0, 1000)
            out_count = int((~valid).sum())
            if out_count > 0:
                logger.warning(
                    "Ano %s, coluna %s: descartando %d valores fora do intervalo [0,1000] (geo).",
                    year,
                    col,
                    out_count,
                )
            df[col] = series.where(valid)

        grouped = df.groupby(
            ["ANO", "SG_UF_PROVA", "CO_MUNICIPIO_PROVA", "NO_MUNICIPIO_PROVA"],
            dropna=True,
        )
        agg_parts: list[pd.Series] = []
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
        geo_df = pd.DataFrame(
            columns=["ANO", *GEO_COLUMNS]
            + [f"{n}_{suf}" for n in DEFAULT_NOTA_COLUMNS for suf in ("count", "mean")]
        )

    geo_path = gold_dir() / "tb_notas_geo.parquet"
    write_parquet(geo_df, geo_path)
    return geo_df


def build_tb_notas_geo_uf_from_cleaned(years: Iterable[int]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning("Arquivo limpo não encontrado para o ano %s em %s; ignorando.", year, path)
            continue

        df = read_parquet(path)
        df = _clean_columns(df, year, extra_columns=["SG_UF_PROVA"])

        if "SG_UF_PROVA" not in df.columns:
            logger.warning("Coluna SG_UF_PROVA ausente para o ano %s; geo (UF) ficará vazio.", year)
            continue

        for col in DEFAULT_NOTA_COLUMNS:
            series = pd.to_numeric(df[col], errors="coerce")
            valid = series.between(0, 1000)
            df[col] = series.where(valid)

        grouped = df.groupby(["ANO", "SG_UF_PROVA"], dropna=True)
        
        # Lógica de agregação robusta para 'INSCRITOS'
        if "ID_INSCRICAO" in df.columns:
            inscritos_agg = grouped["ID_INSCRICAO"].nunique().rename("INSCRITOS")
        else:
            logger.warning(
                "ID_INSCRICAO não encontrado para o ano %s. Usando o tamanho do grupo como contagem de inscritos.",
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
    logger.info("Tabela Geográfica por UF gerada em %s.", geo_path)
    return geo_df


def build_tb_notas_histogram_from_cleaned(
    years: Iterable[int],
    bins: int = 50,
    range_min: int = 0,
    range_max: int = 1000,
) -> pd.DataFrame:
    all_hist_frames = []
    bin_edges = np.linspace(range_min, range_max, bins + 1)

    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning("Arquivo limpo não encontrado para o ano %s; ignorando.", year, path)
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
    logger.info("Tabela de histograma gerada em %s.", hist_path)
    return final_df


__all__ = [
    "build_tb_notas_parquet_streaming",
    "build_tb_notas_stats_from_cleaned",
    "build_tb_notas_geo_from_cleaned",
    "build_tb_notas_geo_uf_from_cleaned",
    "build_tb_notas_histogram_from_cleaned",
]
