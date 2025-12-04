import duckdb
from enem_project.config.settings import settings
import pandas as pd

db_path = settings.DATA_DIR / "enem.duckdb"
print(f"Connecting to {db_path}")

try:
    con = duckdb.connect(str(db_path), read_only=True)
    
    print("Checking PARTIAL...")
    
    sql = "SELECT ANO, NO_MUNICIPIO_PROVA, TP_COR_RACA, COUNT(*) as group_size, AVG(NOTA_MATEMATICA) as mat, AVG(NOTA_CIENCIAS_NATUREZA) as nat, AVG(NOTA_CIENCIAS_HUMANAS) as hum, AVG(NOTA_LINGUAGENS_CODIGOS) as lin, AVG(NOTA_REDACAO) as red FROM gold_classes WHERE ANO >= 2009 GROUP BY ANO, NO_MUNICIPIO_PROVA, TP_COR_RACA HAVING COUNT(*) > 50 AND ((mat IS NOT NULL OR nat IS NOT NULL OR hum IS NOT NULL OR lin IS NOT NULL OR red IS NOT NULL) AND (mat IS NULL OR nat IS NULL OR hum IS NULL OR lin IS NULL OR red IS NULL)) ORDER BY group_size DESC LIMIT 20"
    
    df_partial = con.execute(sql).fetchdf()
    
    if len(df_partial) > 0:
        print(f"Found {len(df_partial)} groups with PARTIAL averages!")
        print(df_partial)
    else:
        print("No groups found with PARTIAL averages.")

except Exception as e:
    print(f"Error: {e}")
