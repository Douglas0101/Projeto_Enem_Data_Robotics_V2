import duckdb
import pandas as pd
from enem_project.config.settings import settings

db_path = settings.DATA_DIR / "enem.duckdb"
print(f"Connecting to {db_path}")

try:
    con = duckdb.connect(str(db_path), read_only=True)
    print("Connected.")
    
    # Check tb_notas_geo
    print("\nChecking tb_notas_geo schema:")
    schema = con.execute("DESCRIBE tb_notas_geo").fetchdf()
    print(schema)
    
except Exception as e:
    print(f"Error: {e}")
