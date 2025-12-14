"""
Testes para os pipelines de limpeza e engenharia de classes.

Este módulo contém testes unitários e de integração para:
- Pipeline de limpeza de dados (cleaning)
- Pipeline de engenharia de classes (class engineering)
- Processamento em streaming
"""

from pathlib import Path

import pandas as pd

from enem_project.data.cleaning.pipeline import run_cleaning_pipeline
from enem_project.data.cleaning.streaming import stream_clean_to_parquet
from enem_project.data.class_engineering.streaming import stream_class_pipeline
from enem_project.data.class_engineering.transformers import run_class_pipeline
from enem_project.data.class_engineering import (
    transformers as class_transformers,
)
from enem_project.data.metadata import save_metadata
from enem_project.data import metadata as metadata_module


def _sample_metadata(year: int) -> pd.DataFrame:
    """Gera metadata de exemplo para testes."""
    return pd.DataFrame(
        [
            {
                "ano": year,
                "nome_original": "ID_INSCRICAO",
                "nome_padrao": "ID_INSCRICAO",
                "descricao": "",
                "tipo_padrao": "string",
                "dominio_valores": None,
            },
            {
                "ano": year,
                "nome_original": "NU_IDADE",
                "nome_padrao": "NU_IDADE",
                "descricao": "",
                "tipo_padrao": "int",
                "dominio_valores": None,
            },
            {
                "ano": year,
                "nome_original": "NOTA_MATEMATICA",
                "nome_padrao": "NOTA_MATEMATICA",
                "descricao": "",
                "tipo_padrao": "float",
                "dominio_valores": None,
            },
            {
                "ano": year,
                "nome_original": "NOTA_LINGUAGENS_CODIGOS",
                "nome_padrao": "NOTA_LINGUAGENS_CODIGOS",
                "descricao": "",
                "tipo_padrao": "float",
                "dominio_valores": None,
            },
            {
                "ano": year,
                "nome_original": "RENDA_FAMILIAR",
                "nome_padrao": "RENDA_FAMILIAR",
                "descricao": "",
                "tipo_padrao": "string",
                "dominio_valores": ["A", "B", "C"],
            },
        ]
    )


def test_cleaning_pipeline_filters_invalid_and_duplicates(tmp_path: Path, monkeypatch):
    """Testa se pipeline de limpeza filtra inválidos e duplicados."""
    # pylint: disable=import-outside-toplevel
    from enem_project.config import paths as paths_module

    data_dir = tmp_path / "data"
    gold_dir = data_dir / "02_gold"
    gold_dir.mkdir(parents=True)

    monkeypatch.setattr(paths_module, "gold_dir", lambda: gold_dir)
    monkeypatch.setattr(metadata_module, "gold_dir", lambda: gold_dir)
    save_metadata(_sample_metadata(2016))

    df = pd.DataFrame(
        {
            "ID_INSCRICAO": ["1", "1", "2", "3", "4"],
            "NU_IDADE": [16, 16, 17, 18, 200],
            "NOTA_MATEMATICA": [500, 500, 600, 650, 700],
            "NOTA_LINGUAGENS_CODIGOS": [550, 550, 580, 620, 580],
            "RENDA_FAMILIAR": ["A", "A", "Z", "C", "B"],
        }
    )

    artifacts = run_cleaning_pipeline(df, 2016)

    assert len(artifacts.cleaned_df) == 3  # remove inválidos + duplicado
    assert artifacts.invalid_rows.shape[0] == 1
    assert len(artifacts.duplicates) == 1
    assert "UNKNOWN" in artifacts.cleaned_df["RENDA_FAMILIAR"].values
    assert not artifacts.cleaning_report.empty


def test_class_pipeline_generates_expected_columns(tmp_path: Path, monkeypatch):
    """Testa se pipeline de classes gera colunas esperadas."""
    # pylint: disable=import-outside-toplevel
    from enem_project.config import paths as paths_module

    data_dir = tmp_path / "data"
    gold_dir = data_dir / "02_gold"
    gold_dir.mkdir(parents=True)
    monkeypatch.setattr(paths_module, "gold_dir", lambda: gold_dir)
    monkeypatch.setattr(metadata_module, "gold_dir", lambda: gold_dir)

    save_metadata(_sample_metadata(2016))

    df_clean = pd.DataFrame(
        {
            "ID_INSCRICAO": ["1"],
            "NU_IDADE": [18],
            "NOTA_MATEMATICA": [650],
            "NOTA_LINGUAGENS_CODIGOS": [600],
            "RENDA_FAMILIAR": ["B"],
        }
    )

    result = run_class_pipeline(df_clean)
    assert "CLASS_FAIXA_ETARIA" in result.classes_df.columns
    assert "CLASS_NOTA_GLOBAL" in result.classes_df.columns
    assert "CLASS_RENDA_FAMILIAR" in result.classes_df.columns
    faixa_sum = result.summary_df[
        result.summary_df["class_name"] == "CLASS_FAIXA_ETARIA"
    ]["total"].sum()
    assert faixa_sum == 1


def test_class_pipeline_respects_chunk_size(monkeypatch):
    """Testa se pipeline de classes respeita chunk_size."""
    df = pd.DataFrame(
        {
            "ID_INSCRICAO": [str(i) for i in range(10)],
            "NU_IDADE": [18] * 10,
            "NOTA_MATEMATICA": [600] * 10,
            "NOTA_LINGUAGENS_CODIGOS": [620] * 10,
            "RENDA_FAMILIAR": ["A"] * 10,
        }
    )

    call_counter = {"count": 0}
    original_apply = class_transformers.apply_class_definitions

    def _spy(df_chunk, defs):
        call_counter["count"] += 1
        return original_apply(df_chunk, defs)

    monkeypatch.setattr(class_transformers, "apply_class_definitions", _spy)

    result = run_class_pipeline(df, chunk_size=3)
    assert len(result.classes_df) == len(df)
    # 10 linhas em chunks de 3 → pelo menos 4 chamadas
    assert call_counter["count"] >= 4


def test_stream_cleaning_matches_batch(tmp_path: Path):
    """Testa se streaming de limpeza produz mesmo resultado que batch."""
    metadata = _sample_metadata(2016)
    df = pd.DataFrame(
        {
            "ID_INSCRICAO": ["1", "1", "2", "4"],
            "NU_IDADE": [16, 16, 17, 250],
            "NOTA_MATEMATICA": [500, 500, 600, 700],
            "NOTA_LINGUAGENS_CODIGOS": [550, 550, 580, 580],
            "RENDA_FAMILIAR": ["A", "A", "Z", "B"],
        }
    )
    batch = run_cleaning_pipeline(df.copy(), 2016, metadata)

    silver_path = tmp_path / "silver.parquet"
    clean_path = tmp_path / "cleaned.parquet"
    df.to_parquet(silver_path, index=False)

    streaming = stream_clean_to_parquet(
        silver_path,
        clean_path,
        2016,
        chunk_rows=2,
        metadata=metadata,
    )

    stream_df = pd.read_parquet(clean_path)
    pd.testing.assert_frame_equal(
        stream_df.reset_index(drop=True),
        batch.cleaned_df.reset_index(drop=True),
        check_like=True,
    )
    assert streaming.row_count == len(batch.cleaned_df)
    assert (
        streaming.cleaning_report["affected_rows"].sum()
        == batch.cleaning_report["affected_rows"].sum()
    )
    assert len(streaming.invalid_rows) == len(batch.invalid_rows)


def test_stream_class_pipeline_matches_batch(tmp_path: Path):
    """Testa se streaming de classes produz mesmo resultado que batch."""
    df_clean = pd.DataFrame(
        {
            "ID_INSCRICAO": ["1", "2", "3"],
            "NU_IDADE": [18, 30, 45],
            "NOTA_MATEMATICA": [650, 450, 520],
            "NOTA_LINGUAGENS_CODIGOS": [600, 500, 480],
            "RENDA_FAMILIAR": ["B", "A", "C"],
        }
    )
    clean_path = tmp_path / "clean.parquet"
    classes_path = tmp_path / "classes.parquet"
    df_clean.to_parquet(clean_path, index=False)

    stream_result = stream_class_pipeline(clean_path, classes_path, chunk_rows=2)
    df_stream = pd.read_parquet(classes_path)

    batch_result = run_class_pipeline(df_clean)
    pd.testing.assert_frame_equal(
        df_stream.reset_index(drop=True),
        batch_result.classes_df.reset_index(drop=True),
        check_like=True,
    )
    summary_stream = stream_result.summary_df.sort_values(
        ["class_name", "class_value"]
    ).reset_index(drop=True)
    summary_batch = batch_result.summary_df.sort_values(
        ["class_name", "class_value"]
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(summary_stream, summary_batch, check_like=True)


def test_class_pipeline_handles_pd_na_scores():
    """
    Garante que a engenharia de classes lida corretamente com notas
    do tipo pandas.NA / Float64, sem lançar exceções e atribuindo
    rótulos coerentes para CLASS_NOTA_GLOBAL.
    """
    df = pd.DataFrame(
        {
            "ID_INSCRICAO": ["1", "2", "3"],
            "NU_IDADE": [18, 19, 20],
            "NOTA_MATEMATICA": [pd.NA, 700.0, pd.NA],
            "NOTA_LINGUAGENS_CODIGOS": [650.0, pd.NA, pd.NA],
            "RENDA_FAMILIAR": ["A", "B", "C"],
        }
    )

    result = run_class_pipeline(df)
    classes_df = result.classes_df

    # Primeira linha: apenas linguagens presente → média = 650 → ALTA
    assert classes_df.loc[0, "CLASS_NOTA_GLOBAL"] == "ALTA"
    # Segunda linha: apenas matemática presente → média = 700 → ALTA
    assert classes_df.loc[1, "CLASS_NOTA_GLOBAL"] == "ALTA"
    # Terceira linha: ambas ausentes → NA
    assert classes_df.loc[2, "CLASS_NOTA_GLOBAL"] == "NA"
