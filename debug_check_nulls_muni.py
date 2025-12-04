import duckdb
from enem_project.config.settings import settings
import pandas as pd

db_path = settings.DATA_DIR / "enem.duckdb"
print(f"Connecting to {db_path}")

try:
    con = duckdb.connect(str(db_path), read_only=True)
    
    print("\n--- Checking for incomplete exam sets in gold_classes (2009-2024) BY MUNICIPALITY ---")
    
    # We limit to having > 100 students, as per the API query
    df_missing = con.execute("""
        SELECT 
            ANO,
            NO_MUNICIPIO_PROVA,
            TP_COR_RACA,
            COUNT(*) as group_size,
            AVG(NOTA_MATEMATICA) as mat,
            AVG(NOTA_CIENCIAS_NATUREZA) as nat,
            AVG(NOTA_CIENCIAS_HUMANAS) as hum,
            AVG(NOTA_LINGUAGENS_CODIGOS) as lin,
            AVG(NOTA_REDACAO) as red
        FROM gold_classes
        WHERE ANO >= 2009
        GROUP BY ANO, NO_MUNICIPIO_PROVA, TP_COR_RACA
        HAVING COUNT(*) > 100 
           AND (
            mat IS NULL OR 
            nat IS NULL OR 
            hum IS NULL OR 
            lin IS NULL OR 
            red IS NULL
        )
        ORDER BY group_size DESC
        LIMIT 20
    """).fetchdf()
    
    if len(df_missing) > 0:
        print(f"Found {len(df_missing)} groups with missing averages!")
        print(df_missing)
    else:
        print("No groups found with missing averages (group > 100) for years >= 2009.")

except Exception as e:
    print(f"Error: {e}")
