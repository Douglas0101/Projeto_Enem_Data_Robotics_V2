import pandas as pd
from pathlib import Path

from enem_project.data.metadata import _collect_small_domain
from enem_project.data.raw_to_silver import clean_and_standardize
from enem_project.infra.io import read_csv
from enem_project.config import paths as paths_module
from enem_project.config.settings import Settings, settings as global_settings


def test_run_raw_to_silver_pipeline(tmp_path: Path, monkeypatch):
    """
    Tests the full raw_to_silver pipeline for a sample year (2022).
    It creates a dummy raw CSV, runs the pipeline, and checks the silver output.
    """
    # 1. SETUP: Create fake raw data directory and file
    year = 2022
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "00_raw" / f"microdados_enem_{year}" / "DADOS"
    raw_dir.mkdir(parents=True)
    raw_file_path = raw_dir / f"MICRODADOS_ENEM_{year}.csv"

    dummy_data = {
        "NU_INSCRICAO": [1, 2],
        "SEXO": ["m", "F"],
        "UF_PROVA": ["sp", "RJ"],
        "NU_ANO": [year, year],
        "NU_NOTA_CN": ["550,5", "1200"],  # segunda nota fora de faixa será descartada
        "NU_IDADE": [18, 200],  # idade inválida será descartada
        "EXTRA_COLUMN": ["A", "B"],
    }
    pd.DataFrame(dummy_data).to_csv(raw_file_path, index=False, sep=";")

    # Redireciona paths/settings para o diretório temporário
    custom_settings = Settings(
        PROJECT_ROOT=tmp_path,
        DATA_DIR=data_dir,
        YEARS=global_settings.YEARS,
    )
    monkeypatch.setattr(paths_module, "settings", custom_settings)

    import enem_project.data.raw_to_silver as rts

    monkeypatch.setattr(rts, "paths", paths_module)
    monkeypatch.setattr(rts, "settings", custom_settings)

    # 2. EXECUTION: Run the pipeline logic end-to-end
    results = rts.run_raw_to_silver(year)
    assert results
    expected_silver_file = results[0].path

    # 3. ASSERTION: Check if the output is correct
    assert expected_silver_file.exists()

    df_silver = pd.read_parquet(expected_silver_file)
    assert "ID_INSCRICAO" in df_silver.columns
    assert "TP_SEXO" in df_silver.columns
    assert "NOTA_CIENCIAS_NATUREZA" in df_silver.columns
    assert "ANO" in df_silver.columns
    assert "EXTRA_COLUMN" not in df_silver.columns  # Column was dropped
    assert list(df_silver["TP_SEXO"]) == ["M", "F"]
    assert df_silver["NOTA_CIENCIAS_NATUREZA"].iloc[0] == 550.5
    assert pd.isna(df_silver["NOTA_CIENCIAS_NATUREZA"].iloc[1])
    assert pd.isna(df_silver["NU_IDADE"].iloc[1])
    assert df_silver["ANO"].iloc[0] == year
    assert len(df_silver) == 2


def test_collect_small_domain_returns_ordered_unique_values():
    series = pd.Series(["A", "B", "A", None, "B", "C"])
    domain = _collect_small_domain(series, max_size=5)
    assert domain == ["A", "B", "C"]


def test_collect_small_domain_returns_none_when_limit_exceeded():
    # As soon as the limit is ultrapassed, None is returned (no massive allocations).
    series = pd.Series([f"valor_{i}" for i in range(10)])
    domain = _collect_small_domain(series, max_size=3)
    assert domain is None


def test_clean_and_standardize_handles_aliases_and_ranges():
    df = pd.DataFrame(
        {
            "INSCRICAO": ["001", "002"],
            "NOTA_MT": ["700,2", "1010"],  # segunda nota fora da faixa
            "MUNICIPIO_PROVA": ["SAO PAULO", "RIO"],
        }
    )
    clean = clean_and_standardize(df, 2010)
    assert list(clean["ID_INSCRICAO"]) == ["001", "002"]
    assert clean["NOTA_MATEMATICA"].iloc[0] == 700.2
    assert pd.isna(clean["NOTA_MATEMATICA"].iloc[1])
    assert list(clean["NO_MUNICIPIO_PROVA"]) == ["SAO PAULO", "RIO"]
    assert clean["ANO"].nunique() == 1


def test_read_csv_fallbacks_to_chunked_pandas_for_latin1(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    df_expected = pd.DataFrame(
        {
            "COL_A": ["João", "Maria", "José"],
            "COL_B": [1, 2, 3],
        }
    )
    df_expected.to_csv(csv_path, sep=";", index=False, encoding="latin-1")

    df = read_csv(csv_path, encoding="latin-1", chunk_rows=1)
    assert len(df) == 3
    assert list(df["COL_A"]) == ["João", "Maria", "José"]
    assert list(df["COL_B"]) == [1, 2, 3]


def test_raw_data_path_handles_lowercase_filename(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    target_dir = data_dir / "00_raw" / "microdados_enem_2016" / "DADOS"
    target_dir.mkdir(parents=True)
    lowercase_file = target_dir / "microdados_enem_2016.csv"
    lowercase_file.write_text("ID;VAL\n1;foo\n")

    custom_settings = Settings(
        PROJECT_ROOT=tmp_path,
        DATA_DIR=data_dir,
        YEARS=global_settings.YEARS,
    )
    monkeypatch.setattr(paths_module, "settings", custom_settings)

    resolved = paths_module.raw_data_path(2016)
    assert resolved == lowercase_file


def test_build_tb_notas_and_stats(tmp_path: Path, monkeypatch):
    """
    Garante que o módulo silver_to_gold constrói corretamente as tabelas
    tb_notas e tb_notas_stats a partir da camada limpa.
    """
    from enem_project.config import paths as paths_module_local
    from enem_project.data import silver_to_gold

    data_root = tmp_path / "data"
    gold_root = data_root / "02_gold"
    cleaned_root = gold_root / "cleaned"
    cleaned_root.mkdir(parents=True)

    # Redireciona gold_dir() para o diretório temporário
    monkeypatch.setattr(paths_module_local, "gold_dir", lambda: gold_root)
    monkeypatch.setattr(silver_to_gold, "gold_dir", lambda: gold_root)

    years = (2019, 2020)
    for year in years:
        df = pd.DataFrame(
            {
                "ANO": [year, year],
                "ID_INSCRICAO": [f"{year}1", f"{year}2"],
                "TP_SEXO": ["M", "F"],
                "NU_IDADE": [18, 19],
                "NOTA_CIENCIAS_NATUREZA": [500.0, 600.0],
                "NOTA_CIENCIAS_HUMANAS": [550.0, 650.0],
                "NOTA_LINGUAGENS_CODIGOS": [580.0, 680.0],
                "NOTA_MATEMATICA": [520.0, 720.0],
                "NOTA_REDACAO": [600.0, 700.0],
            }
        )
        df.to_parquet(
            cleaned_root / f"microdados_enem_{year}_clean.parquet",
            index=False,
        )

    silver_to_gold.build_tb_notas_parquet_streaming(years)
    tb_notas_path = gold_root / "tb_notas.parquet"
    assert tb_notas_path.exists()
    tb_notas = pd.read_parquet(tb_notas_path)
    assert set(tb_notas["ANO"].unique()) == set(years)

    stats = silver_to_gold.build_tb_notas_stats_from_cleaned(years)
    stats_path = gold_root / "tb_notas_stats.parquet"
    assert stats_path.exists()
    assert set(stats["ANO"]) == set(years)
    assert "TOTAL_INSCRITOS" in stats.columns
    assert "IDADE_mean" in stats.columns
    assert stats.loc[stats["ANO"] == years[0], "TOTAL_INSCRITOS"].iat[0] == 2

    for prefix in [
        "NOTA_CIENCIAS_NATUREZA",
        "NOTA_CIENCIAS_HUMANAS",
        "NOTA_LINGUAGENS_CODIGOS",
        "NOTA_MATEMATICA",
        "NOTA_REDACAO",
    ]:
        for suffix in ["count", "mean", "std", "min", "median", "max"]:
            assert f"{prefix}_{suffix}" in stats.columns

    # Também valida construção da tabela geográfica com as mesmas bases limpas.
    geo = silver_to_gold.build_tb_notas_geo_from_cleaned(years)
    assert "ANO" in geo.columns
    for col in [
        "NOTA_CIENCIAS_NATUREZA_mean",
        "NOTA_CIENCIAS_NATUREZA_count",
    ]:
        assert col in geo.columns


def test_build_tb_notas_parquet_streaming_handles_mixed_dtypes(
    tmp_path: Path, monkeypatch
):
    """
    Garante que build_tb_notas_parquet_streaming não falha quando
    diferentes anos possuem NOTA_REDACAO com dtypes distintos
    (ex.: int em um ano e float em outro).
    """
    from enem_project.config import paths as paths_module_local
    from enem_project.data import silver_to_gold
    from pandas.api.types import is_float_dtype

    data_root = tmp_path / "data"
    gold_root = data_root / "02_gold"
    cleaned_root = gold_root / "cleaned"
    cleaned_root.mkdir(parents=True)

    # Redireciona gold_dir() para o diretório temporário também na função local.
    monkeypatch.setattr(paths_module_local, "gold_dir", lambda: gold_root)
    monkeypatch.setattr(silver_to_gold, "gold_dir", lambda: gold_root)

    years = (1998, 1999)

    # Ano 1998 com NOTA_REDACAO inteira
    df_1998 = pd.DataFrame(
        {
            "ANO": [1998, 1998],
            "ID_INSCRICAO": [1, 2],
            "NOTA_REDACAO": [600, 700],  # int
        }
    )
    df_1998.to_parquet(
        cleaned_root / "microdados_enem_1998_clean.parquet",
        index=False,
    )

    # Ano 1999 com NOTA_REDACAO float
    df_1999 = pd.DataFrame(
        {
            "ANO": [1999, 1999],
            "ID_INSCRICAO": [3, 4],
            "NOTA_REDACAO": [650.5, 750.0],  # float
        }
    )
    df_1999.to_parquet(
        cleaned_root / "microdados_enem_1999_clean.parquet",
        index=False,
    )

    total_rows = silver_to_gold.build_tb_notas_parquet_streaming(years)
    tb_notas_path = gold_root / "tb_notas.parquet"
    assert tb_notas_path.exists()
    assert total_rows == 4

    tb_notas = pd.read_parquet(tb_notas_path)
    assert set(tb_notas["ANO"].unique()) == set(years)
    # A coluna de redação deve estar normalizada como float
    assert is_float_dtype(tb_notas["NOTA_REDACAO"].dtype)


def test_build_tb_notas_parquet_streaming_uses_alias_columns(
    tmp_path: Path, monkeypatch
):
    """
    Garante que o modo streaming lê apenas colunas necessárias e ainda
    reconstroi as notas canônicas a partir das colunas NU_NOTA_*.
    """
    from enem_project.config import paths as paths_module_local
    from enem_project.data import silver_to_gold

    data_root = tmp_path / "data"
    gold_root = data_root / "02_gold"
    cleaned_root = gold_root / "cleaned"
    cleaned_root.mkdir(parents=True)

    monkeypatch.setattr(paths_module_local, "gold_dir", lambda: gold_root)
    monkeypatch.setattr(silver_to_gold, "gold_dir", lambda: gold_root)
    monkeypatch.setenv("ENEM_PARQUET_STREAM_ROWS", "1")

    year = 2005
    df = pd.DataFrame(
        {
            "NU_INSCRICAO": [10, 11, 12],
            "NU_NOTA_CN": [450, 470, 480],
            "NU_NOTA_MT": [500, 510, 520],
        }
    )
    df.to_parquet(cleaned_root / f"microdados_enem_{year}_clean.parquet", index=False)

    total_rows = silver_to_gold.build_tb_notas_parquet_streaming((year,))
    assert total_rows == 3

    tb_notas = pd.read_parquet(gold_root / "tb_notas.parquet")
    assert list(tb_notas["ANO"]) == [year] * 3
    assert list(tb_notas["NOTA_CIENCIAS_NATUREZA"]) == [450.0, 470.0, 480.0]
    assert list(tb_notas["NOTA_MATEMATICA"]) == [500.0, 510.0, 520.0]
