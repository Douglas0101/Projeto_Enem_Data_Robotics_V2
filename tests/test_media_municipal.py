"""
Testes para o pipeline de Média Municipal (evolução temporal por município).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from enem_project.data.silver_to_gold import (
    build_tb_media_municipal_from_cleaned,
    DEFAULT_NOTA_COLUMNS,
)


# ---------------------------------------------------------------------------
# UNIT TESTS: build_tb_media_municipal_from_cleaned
# ---------------------------------------------------------------------------


class TestBuildTbMediaMunicipalFromCleaned:
    """Testes de integração para o pipeline de média municipal."""

    def test_pipeline_gera_tabela_corretamente(
        self, tmp_path: Path, monkeypatch
    ):
        """Pipeline gera tabela agregada corretamente."""
        from enem_project.config import paths as paths_module
        from enem_project.data import silver_to_gold

        # Setup: diretórios temporários
        data_root = tmp_path / "data"
        gold_root = data_root / "02_gold"
        cleaned_root = gold_root / "cleaned"
        cleaned_root.mkdir(parents=True)

        # Redireciona paths
        monkeypatch.setattr(paths_module, "gold_dir", lambda: gold_root)
        monkeypatch.setattr(silver_to_gold, "gold_dir", lambda: gold_root)

        # Cria dados de teste para 2023
        year = 2023
        df = pd.DataFrame({
            "ANO": [year] * 4,
            "SG_UF_PROVA": ["SP", "SP", "RJ", "RJ"],
            "CO_MUNICIPIO_PROVA": ["3550308", "3550308", "3304557", "3304557"],
            "NO_MUNICIPIO_PROVA": ["São Paulo", "São Paulo", "Rio de Janeiro", "Rio de Janeiro"],
            "NOTA_CIENCIAS_NATUREZA": [500.0, 700.0, 600.0, 850.0],
            "NOTA_CIENCIAS_HUMANAS": [500.0, 700.0, 600.0, 850.0],
            "NOTA_LINGUAGENS_CODIGOS": [500.0, 700.0, 600.0, 850.0],
            "NOTA_MATEMATICA": [500.0, 700.0, 600.0, 850.0],
            "NOTA_REDACAO": [500.0, 700.0, 600.0, 850.0],
        })
        df.to_parquet(
            cleaned_root / f"microdados_enem_{year}_clean.parquet",
            index=False,
        )

        # Executa pipeline
        result = silver_to_gold.build_tb_media_municipal_from_cleaned((year,))

        # Verifica resultado
        assert not result.empty
        expected_cols = {
            "ANO",
            "SG_UF_PROVA",
            "CO_MUNICIPIO_PROVA",
            "NO_MUNICIPIO_PROVA",
            "QTD_ALUNOS",
            "MEDIA_CN",
            "MEDIA_CH",
            "MEDIA_LC",
            "MEDIA_MT",
            "MEDIA_RED",
            "MEDIA_FINAL",
        }
        assert expected_cols.issubset(set(result.columns))

        # Verifica que há 2 municípios
        assert len(result) == 2

        # Verifica médias
        sp_row = result[result["NO_MUNICIPIO_PROVA"] == "São Paulo"].iloc[0]
        assert sp_row["QTD_ALUNOS"] == 2
        assert sp_row["MEDIA_FINAL"] == 600.0  # (500 + 700) / 2

        rj_row = result[result["NO_MUNICIPIO_PROVA"]
                        == "Rio de Janeiro"].iloc[0]
        assert rj_row["QTD_ALUNOS"] == 2
        assert rj_row["MEDIA_FINAL"] == 725.0  # (600 + 850) / 2

        # Verifica arquivo gerado
        out_path = gold_root / "tb_media_municipal.parquet"
        assert out_path.exists()

    def test_pipeline_filtra_anos_antes_2009(
        self, tmp_path: Path, monkeypatch
    ):
        """Pipeline ignora anos antes de 2009 (sem dados de município)."""
        from enem_project.config import paths as paths_module
        from enem_project.data import silver_to_gold

        # Setup
        data_root = tmp_path / "data"
        gold_root = data_root / "02_gold"
        cleaned_root = gold_root / "cleaned"
        cleaned_root.mkdir(parents=True)

        monkeypatch.setattr(paths_module, "gold_dir", lambda: gold_root)
        monkeypatch.setattr(silver_to_gold, "gold_dir", lambda: gold_root)

        # Cria arquivo para ano 2008 (deve ser ignorado)
        year = 2008
        df = pd.DataFrame({
            "ANO": [year],
            "SG_UF_PROVA": ["SP"],
            "CO_MUNICIPIO_PROVA": ["3550308"],
            "NO_MUNICIPIO_PROVA": ["São Paulo"],
            "NOTA_CIENCIAS_NATUREZA": [500.0],
            "NOTA_CIENCIAS_HUMANAS": [500.0],
            "NOTA_LINGUAGENS_CODIGOS": [500.0],
            "NOTA_MATEMATICA": [500.0],
            "NOTA_REDACAO": [500.0],
        })
        df.to_parquet(
            cleaned_root / f"microdados_enem_{year}_clean.parquet",
            index=False,
        )

        # Executa pipeline com ano < 2009
        result = silver_to_gold.build_tb_media_municipal_from_cleaned((2008,))

        # Deve retornar vazio
        assert result.empty

    def test_pipeline_multiplos_anos(
        self, tmp_path: Path, monkeypatch
    ):
        """Pipeline processa múltiplos anos corretamente."""
        from enem_project.config import paths as paths_module
        from enem_project.data import silver_to_gold

        # Setup
        data_root = tmp_path / "data"
        gold_root = data_root / "02_gold"
        cleaned_root = gold_root / "cleaned"
        cleaned_root.mkdir(parents=True)

        monkeypatch.setattr(paths_module, "gold_dir", lambda: gold_root)
        monkeypatch.setattr(silver_to_gold, "gold_dir", lambda: gold_root)

        # Cria arquivos para 2023 e 2024
        for year in [2023, 2024]:
            df = pd.DataFrame({
                "ANO": [year] * 2,
                "SG_UF_PROVA": ["SP", "SP"],
                "CO_MUNICIPIO_PROVA": ["3550308", "3550308"],
                "NO_MUNICIPIO_PROVA": ["São Paulo", "São Paulo"],
                "NOTA_CIENCIAS_NATUREZA": [500.0, 600.0],
                "NOTA_CIENCIAS_HUMANAS": [500.0, 600.0],
                "NOTA_LINGUAGENS_CODIGOS": [500.0, 600.0],
                "NOTA_MATEMATICA": [500.0, 600.0],
                "NOTA_REDACAO": [500.0, 600.0],
            })
            df.to_parquet(
                cleaned_root / f"microdados_enem_{year}_clean.parquet",
                index=False,
            )

        # Executa pipeline
        result = silver_to_gold.build_tb_media_municipal_from_cleaned(
            (2023, 2024))

        # Deve ter 2 linhas (1 município × 2 anos)
        assert len(result) == 2
        assert set(result["ANO"].unique()) == {2023, 2024}


# ---------------------------------------------------------------------------
# Note: API tests for get_media_municipal endpoint should follow the
# existing pattern in test_api_dashboard_core.py using FakeAgent.
# ---------------------------------------------------------------------------
