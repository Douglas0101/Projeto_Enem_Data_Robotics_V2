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

try:  # pragma: no cover - duckdb é opcional, mas acelera agregações grandes
    import duckdb
except ImportError:  # pragma: no cover
    duckdb = None

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
            df[cat_col] = pd.to_numeric(df[cat_col], errors="coerce").astype("Int16")
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
        logger.info("Construindo tb_notas (streaming) a partir de {}", path)

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

    logger.info("tb_notas gerado em {} com {} linhas (streaming).", tb_notas_path, total_rows)
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
                    "Ano {}: descartando {} idades fora do intervalo [8,120] para estatísticas anuais.",
                    year,
                    out_age,
                )
            age_series = age_series.where(valid_age)
            age_valid = age_series.dropna()
            if age_valid.empty:
                record.update(
                    {
                        # Mantém como NaN para não sinalizar falsos positivos nos data checks.
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
                    "Ano {}, coluna {}: descartando {} valores fora do intervalo [0,1000].",
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

    # Preenche apenas colunas de nota com 0 (idade permanece NaN para não gerar falsos avisos).
    nota_cols = [c for c in df_stats.columns if c.startswith("NOTA_")]
    age_cols = [c for c in df_stats.columns if c.startswith("IDADE_")]
    if nota_cols:
        df_stats[nota_cols] = df_stats[nota_cols].fillna(0).infer_objects(copy=False)
    if age_cols:
        df_stats[age_cols] = df_stats[age_cols].infer_objects(copy=False)

    return df_stats


def _geo_empty_schema() -> list[str]:
    return ["ANO", *GEO_COLUMNS] + [f"{n}_{suf}" for n in DEFAULT_NOTA_COLUMNS for suf in ("count", "mean")]


def _geo_requires_columns(path: Path, required: list[str]) -> bool:
    pf = pq.ParquetFile(path)
    cols = set(pf.schema.names)
    return all(col in cols for col in required)


def _build_geo_duckdb(path: Path, year: int) -> pd.DataFrame:
    required = [*GEO_COLUMNS, *DEFAULT_NOTA_COLUMNS]
    if not _geo_requires_columns(path, required):
        logger.warning(
            "Colunas geográficas ou de notas ausentes para o ano {}; geo ficará vazio (schema preservado).",
            year,
        )
        return pd.DataFrame(columns=_geo_empty_schema())

    col_selects = []
    for col in DEFAULT_NOTA_COLUMNS:
        valid_case = f"CASE WHEN {col} BETWEEN 0 AND 1000 THEN {col} END"
        col_selects.append(f"SUM(CASE WHEN {col} BETWEEN 0 AND 1000 THEN 1 ELSE 0 END) AS {col}_count")
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
    """
    return duckdb.sql(query).df()  # type: ignore[union-attr]


def _build_geo_uf_duckdb(path: Path, year: int) -> pd.DataFrame:
    pf = pq.ParquetFile(path)
    cols = set(pf.schema.names)
    required = {"SG_UF_PROVA", *DEFAULT_NOTA_COLUMNS}
    if not required.issubset(cols):
        logger.warning("Colunas necessárias para geo_uf ausentes no ano {}; retorno vazio.", year)
        return pd.DataFrame()

    has_id = "ID_INSCRICAO" in cols
    inscritos_expr = "COUNT(DISTINCT ID_INSCRICAO)" if has_id else "COUNT(*)"

    col_selects = [f"{inscritos_expr} AS INSCRITOS"]
    for col in DEFAULT_NOTA_COLUMNS:
        valid_case = f"CASE WHEN {col} BETWEEN 0 AND 1000 THEN {col} END"
        col_selects.append(f"SUM(CASE WHEN {col} BETWEEN 0 AND 1000 THEN 1 ELSE 0 END) AS {col}_count")
        col_selects.append(f"AVG({valid_case}) AS {col}_mean")

    query = f"""
    SELECT
        COALESCE(CAST(ANO AS INT), {year}) AS ANO,
        SG_UF_PROVA,
        {", ".join(col_selects)}
    FROM read_parquet('{path.as_posix()}')
    WHERE SG_UF_PROVA IS NOT NULL
    GROUP BY 1,2
    """
    return duckdb.sql(query).df()  # type: ignore[union-attr]


def build_tb_notas_stats_from_cleaned(years: Iterable[int]) -> pd.DataFrame:
    # Calcula stats por ano lendo os Parquets limpos ano a ano
    records: list[dict[str, object]] = []
    columns_to_read = ["ID_INSCRICAO", "NU_IDADE", *DEFAULT_NOTA_COLUMNS]
    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning("Arquivo limpo não encontrado para o ano {} em {}; ignorando.", year, path)
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
    frames: list[pd.DataFrame] = []
    columns_to_read = [*GEO_COLUMNS, *DEFAULT_NOTA_COLUMNS]
    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning("Arquivo limpo não encontrado para o ano {} em {}; ignorando.", year, path)
            continue

        if duckdb is not None:
            try:
                frames.append(_build_geo_duckdb(path, year))
                continue
            except Exception as exc:  # noqa: BLE001
                logger.warning("DuckDB falhou em geo {} ({}); caindo para pandas.", year, exc)

        df = read_parquet(path, columns=columns_to_read)
        df = _clean_columns(df, year, extra_columns=GEO_COLUMNS)

        if not all(col in df.columns for col in GEO_COLUMNS):
            logger.warning(
                "Colunas geográficas ausentes para o ano {}; geo ficará vazio (schema preservado).",
                year,
            )
            empty = pd.DataFrame(columns=_geo_empty_schema())
            frames.append(empty)
            continue

        for col in DEFAULT_NOTA_COLUMNS:
            series = pd.to_numeric(df[col], errors="coerce")
            valid = series.between(0, 1000)
            df[col] = series.where(valid)

        grouped = df.groupby(
            ["ANO", "SG_UF_PROVA", "CO_MUNICIPIO_PROVA", "NO_MUNICIPIO_PROVA"],
            dropna=True,
            observed=False,
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
        geo_df = pd.DataFrame(columns=_geo_empty_schema())

    geo_path = gold_dir() / "tb_notas_geo.parquet"
    write_parquet(geo_df, geo_path)
    return geo_df


def build_tb_notas_geo_uf_from_cleaned(years: Iterable[int]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    columns_to_read = ["SG_UF_PROVA", "ID_INSCRICAO", *DEFAULT_NOTA_COLUMNS]
    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning("Arquivo limpo não encontrado para o ano {} em {}; ignorando.", year, path)
            continue

        if duckdb is not None:
            try:
                frames.append(_build_geo_uf_duckdb(path, year))
                continue
            except Exception as exc:  # noqa: BLE001
                logger.warning("DuckDB falhou em geo_uf {} ({}); caindo para pandas.", year, exc)

        df = read_parquet(path, columns=columns_to_read)
        df = _clean_columns(df, year, extra_columns=["SG_UF_PROVA"])

        if "SG_UF_PROVA" not in df.columns:
            logger.warning("Coluna SG_UF_PROVA ausente para o ano {}; geo (UF) ficará vazio.", year)
            continue

        for col in DEFAULT_NOTA_COLUMNS:
            series = pd.to_numeric(df[col], errors="coerce")
            valid = series.between(0, 1000)
            df[col] = series.where(valid)

        grouped = df.groupby(["ANO", "SG_UF_PROVA"], dropna=True, observed=False)

        if "ID_INSCRICAO" in df.columns:
            inscritos_agg = grouped["ID_INSCRICAO"].nunique().rename("INSCRITOS")
        else:
            logger.warning(
                "ID_INSCRICAO não encontrado para o ano {}. Usando o tamanho do grupo como contagem de inscritos.",
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
    all_hist_frames = []
    bin_edges = np.linspace(range_min, range_max, bins + 1)

    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            logger.warning("Arquivo limpo não encontrado para o ano {}; ignorando.", year, path)
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


def build_tb_socio_economico_from_cleaned(years: Iterable[int]) -> pd.DataFrame:
    """
    Gera a tabela Gold de indicadores socioeconômicos (Renda x Nota),
    aplicando filtros de qualidade (presença) e mapa de classes.
    """
    frames = []
    # Colunas necessárias: Notas + Q006 + Presença
    cols = [
        "Q006",
        "TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT",
        "TP_STATUS_REDACAO",
        *DEFAULT_NOTA_COLUMNS
    ]

    for year in years:
        path = _cleaned_path(year)
        if not path.exists():
            continue
        
        # Leitura otimizada
        try:
            df = read_parquet(path, columns=cols)
        except Exception:
            logger.warning(f"Colunas socioeconômicas ausentes em {path}. Pulando.")
            continue

        # 1. Filtro de Qualidade (Apenas quem foi em tudo e não zerou redação por falta)
        # PRESENCA = 1 (Presente), STATUS_REDACAO = 1 (Sem problemas)
        mask = (
            (df["TP_PRESENCA_CN"] == 1) &
            (df["TP_PRESENCA_CH"] == 1) &
            (df["TP_PRESENCA_LC"] == 1) &
            (df["TP_PRESENCA_MT"] == 1) &
            (df["TP_STATUS_REDACAO"] == 1)
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
        stats = df_valid.groupby("CLASSE")["NOTA_GERAL"].agg(
            LOW="min",
            Q1=lambda x: x.quantile(0.25),
            MEDIAN="median",
            Q3=lambda x: x.quantile(0.75),
            HIGH="max",
            COUNT="count"
        ).reset_index()
        
        stats["ANO"] = year
        frames.append(stats)

    if not frames:
        return pd.DataFrame()

    final_df = pd.concat(frames, ignore_index=True)
    
    # Ordenação lógica das classes para o gráfico
    class_order = ["Classe A (> 20 SM)", "Classe B (10-20 SM)", "Classe C (4-10 SM)", 
                   "Classe D (2-4 SM)", "Classe E (< 2 SM)", "Sem Renda"]
    final_df["CLASSE"] = pd.Categorical(final_df["CLASSE"], categories=class_order, ordered=True)
    final_df = final_df.sort_values("CLASSE")

    out_path = gold_dir() / "tb_socio_economico.parquet"
    write_parquet(final_df, out_path)
    logger.info("Tabela socioeconômica gerada em {}.", out_path)
    return final_df


__all__ = [
    "build_tb_notas_parquet_streaming",
    "build_tb_notas_stats_from_cleaned",
    "build_tb_notas_geo_from_cleaned",
    "build_tb_notas_geo_uf_from_cleaned",
    "build_tb_notas_histogram_from_cleaned",
    "build_tb_socio_economico_from_cleaned",
]
