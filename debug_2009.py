import duckdb
from enem_project.config.settings import settings
import pandas as pd

db_path = settings.DATA_DIR / "enem.duckdb"
print(f"Connecting to {db_path}")

try:
    con = duckdb.connect(str(db_path), read_only=True)
    
    # Query for 2009
    print("\n--- Data for 2009 ---")
    df_2009 = con.execute("""
        SELECT 
            SG_UF_PROVA, 
            INSCRITOS,
            NOTA_MATEMATICA_mean,
            NOTA_CIENCIAS_NATUREZA_mean,
            NOTA_CIENCIAS_HUMANAS_mean,
            NOTA_LINGUAGENS_CODIGOS_mean,
            NOTA_REDACAO_mean
        FROM tb_notas_geo_uf 
        WHERE ANO = 2009
        ORDER BY INSCRITOS DESC
    """).fetchdf()
    
    print(df_2009.head(27)) # Print all states if possible (27 rows) 
    
    print("\n--- Summary Stats for 2009 ---")
    print(df_2009.describe())
    
    print("\n--- Null Checks ---")
    print(df_2009.isnull().sum())

except Exception as e:
    print(f"Error: {e}")
