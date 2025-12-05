import pandas as pd
from pathlib import Path

from enem_project.data.raw_to_silver import clean_and_standardize


def test_clean_and_standardize_preserves_socioeconomic_columns(tmp_path: Path, monkeypatch):
    """
    Verifica se as novas colunas socioeconômicas (Q006) e indicadores de presença/redação
    são preservados durante a limpeza.
    """
    year = 2022
    
    # Mock data with critical columns
    raw_df = pd.DataFrame({
        "NU_INSCRICAO": ["1001", "1002"],
        "NU_ANO": [year, year],
        "Q006": ["A", "B"],
        "TP_PRESENCA_CN": [1, 0],
        "TP_PRESENCA_CH": [1, 0],
        "TP_PRESENCA_LC": [1, 0],
        "TP_PRESENCA_MT": [1, 0],
        "TP_STATUS_REDACAO": [1, 4],
        "NU_NOTA_CN": [500.5, None],
        "EXTRA_TRASH": ["X", "Y"]
    })

    clean_df = clean_and_standardize(raw_df, year)

    # Check if columns exist
    expected_cols = [
        "Q006", "TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", 
        "TP_PRESENCA_MT", "TP_STATUS_REDACAO", "NOTA_CIENCIAS_NATUREZA"
    ]
    for col in expected_cols:
        assert col in clean_df.columns, f"Coluna {col} deveria estar no DataFrame limpo"

    # Check values
    assert clean_df["Q006"].tolist() == ["A", "B"]
    assert clean_df["TP_PRESENCA_CN"].tolist() == [1, 0]
    assert clean_df["NOTA_CIENCIAS_NATUREZA"].iloc[0] == 500.5
    
    # Check if trash was removed
    assert "EXTRA_TRASH" not in clean_df.columns


def test_build_tb_socio_economico_integration(tmp_path: Path, monkeypatch):
    """
    Teste de integração do novo pipeline socioeconômico (silver_to_gold).
    Simula dados limpos e verifica se a agregação por classe gera os percentis corretos.
    """
    from enem_project.data import silver_to_gold
    
    # Setup mock directories
    gold_root = tmp_path / "gold"
    cleaned_root = gold_root / "cleaned"
    cleaned_root.mkdir(parents=True)
    
    monkeypatch.setattr(silver_to_gold, "gold_dir", lambda: gold_root)
    
    year = 2023
    
    # Create mock cleaned data
    # 4 Alunos:
    # 1. Presente, Classe A, Notas altas
    # 2. Presente, Classe A, Notas médias
    # 3. Presente, Classe E, Notas baixas
    # 4. Ausente (deve ser filtrado)
    
    data = {
        "ANO": [year] * 4,
        "ID_INSCRICAO": ["1", "2", "3", "4"],
        "Q006": ["Q", "Q", "B", "B"], # Q=Classe A, B=Classe E
        "TP_PRESENCA_CN": [1, 1, 1, 0],
        "TP_PRESENCA_CH": [1, 1, 1, 0],
        "TP_PRESENCA_LC": [1, 1, 1, 0],
        "TP_PRESENCA_MT": [1, 1, 1, 0],
        "TP_STATUS_REDACAO": [1, 1, 1, 1],
        "NOTA_CIENCIAS_NATUREZA": [800, 700, 400, 0],
        "NOTA_CIENCIAS_HUMANAS": [800, 700, 400, 0],
        "NOTA_LINGUAGENS_CODIGOS": [800, 700, 400, 0],
        "NOTA_MATEMATICA": [800, 700, 400, 0],
        "NOTA_REDACAO": [800, 700, 400, 0],
    }
    
    df_clean = pd.DataFrame(data)
    df_clean.to_parquet(cleaned_root / f"microdados_enem_{year}_clean.parquet")
    
    # Run the new gold builder
    socio_df = silver_to_gold.build_tb_socio_economico_from_cleaned([year])
    
    assert not socio_df.empty
    assert "CLASSE" in socio_df.columns
    assert "MEDIAN" in socio_df.columns
    
    # Verify aggregation logic
    # Classe A (> 20 SM) should have 2 students (IDs 1 and 2). Note avg = (800+700)/2 = 750
    # Classe E (< 2 SM) should have 1 student (ID 3). Note avg = 400
    
    classe_a = socio_df[socio_df["CLASSE"] == "Classe A (> 20 SM)"].iloc[0]
    assert classe_a["COUNT"] == 2
    assert classe_a["MEDIAN"] == 750.0
    assert classe_a["HIGH"] == 800.0
    assert classe_a["LOW"] == 700.0
    
    classe_e = socio_df[socio_df["CLASSE"] == "Classe E (< 2 SM)"].iloc[0]
    assert classe_e["COUNT"] == 1
    assert classe_e["MEDIAN"] == 400.0
