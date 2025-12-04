import duckdb
from enem_project.config.settings import settings
import pandas as pd

db_path = settings.DATA_DIR / "enem.duckdb"
print(f"Connecting to {db_path}")

try:
    con = duckdb.connect(str(db_path), read_only=True)
    
    print("\n--- Checking for incomplete exam sets in gold_classes (2009-2024) ---")
    # logic: count rows where at least one average is NULL
    
    df_missing = con.execute("""
        SELECT 
            ANO,
            TP_COR_RACA,
            COUNT(*) as group_size,
            AVG(NOTA_MATEMATICA) as mat,
            AVG(NOTA_CIENCIAS_NATUREZA) as nat,
            AVG(NOTA_CIENCIAS_HUMANAS) as hum,
            AVG(NOTA_LINGUAGENS_CODIGOS) as lin,
            AVG(NOTA_REDACAO) as red
        FROM gold_classes
        WHERE ANO >= 2009
        GROUP BY ANO, TP_COR_RACA
        HAVING ( 
            mat IS NULL OR 
            nat IS NULL OR 
            hum IS NULL OR 
            lin IS NULL OR 
            red IS NULL
        )
        ORDER BY ANO, group_size DESC
    """).fetchdf()
    
    if len(df_missing) > 0:
        print(f"Found {len(df_missing)} groups with missing averages!")
        print(df_missing)
    else:
        print("No groups found with missing averages for years >= 2009.")

except Exception as e:
    print(f"Error: {e}")
