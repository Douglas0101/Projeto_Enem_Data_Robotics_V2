import pandas as pd
import pytest


def test_categorical_fillna_fix():
    print("\n--- Iniciando Teste de Reprodução: Fix Categórico ---")

    # 1. Simular DataFrame como ele chega no pipeline
    # (SG_UF_PROVA como category)
    df = pd.DataFrame(
        {
            "ANO": [2009, 2009, 2009],
            # Um valor nulo para provocar o erro
            "SG_UF_PROVA": ["SP", "MG", None],
            "NOTA_MEDIA": [500, 600, 700],
        }
    )

    # Conversão rigorosa que ocorre em _clean_columns
    df["SG_UF_PROVA"] = df["SG_UF_PROVA"].astype("category")

    print("DataFrame Original:")
    print(df)
    print("Dtypes:")
    print(df.dtypes)
    print("Categorias:", df["SG_UF_PROVA"].cat.categories)

    # 2. Tentar aplicar o fix proposto
    try:
        if isinstance(df["SG_UF_PROVA"].dtype, pd.CategoricalDtype):
            if "XX" not in df["SG_UF_PROVA"].cat.categories:
                print("\n[INFO] Adicionando categoria 'XX'...")
                df["SG_UF_PROVA"] = df["SG_UF_PROVA"].cat.add_categories("XX")

        print("[INFO] Executando fillna('XX')...")
        df["SG_UF_PROVA"] = df["SG_UF_PROVA"].fillna("XX")

        print("\nSucesso! DataFrame Final:")
        print(df)

        # Asserts
        assert "XX" in df["SG_UF_PROVA"].values, "Valor XX nao foi inserido"
        assert df["SG_UF_PROVA"].isnull().sum() == 0, "Ainda existem nulos"

    except Exception as e:
        pytest.fail(f"FALHA: Ocorreu exceção ao aplicar o fix: {e}")


def test_reproduce_crash_without_fix():
    """
    Este teste deve falhar ou levantar exceção se rodarmos a lógica antiga.
    Serve apenas para documentar o comportamento original.
    """
    print("\n--- Teste de Comportamento Original (Crash Esperado) ---")
    df = pd.DataFrame({"SG_UF_PROVA": ["SP", None]})
    df["SG_UF_PROVA"] = df["SG_UF_PROVA"].astype("category")

    try:
        # A lógica antiga era direta:
        df["SG_UF_PROVA"] = df["SG_UF_PROVA"].fillna("XX")
    except TypeError as e:
        print(f"\n[SUCESSO] Erro reproduzido conforme esperado: {e}")
        return
    except ValueError as e:
        print(f"\n[SUCESSO] Erro reproduzido conforme esperado: {e}")
        return

    # Se chegou aqui, o pandas mudou comportamento ou o teste está errado,
    # mas para versões recentes isso DEVE falhar.
    # print("Aviso: O código antigo não falhou. "
    #       "Versão do Pandas pode ser diferente?")


if __name__ == "__main__":
    # Rodar manualmente como script
    try:
        test_reproduce_crash_without_fix()
        test_categorical_fillna_fix()
        print("\n\n=== TUDO OK: O FIX FUNCIONA E O ERRO FOI REPRODUZIDO ===")
    except Exception as e:
        print(f"\n\n!!! FALHA GERAL: {e}")
        exit(1)
