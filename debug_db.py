import duckdb
import pandas as pd
from enem_project.config.settings import settings

db_path = settings.DATA_DIR / "enem.duckdb"
print(f"Connecting to {db_path}")

try:
    con = duckdb.connect(str(db_path), read_only=True)
    print("Connected.")
    
    # List tables
    tables = con.execute("SHOW TABLES").fetchall()
    print("Tables:", tables)
    
    # Check tb_notas_geo_uf
    if ('tb_notas_geo_uf',) in tables:
        count = con.execute("SELECT COUNT(*) FROM tb_notas_geo_uf").fetchone()[0]
        print(f"Count in tb_notas_geo_uf: {count}")
        
        if count > 0:
            print("Sample data:")
            df = con.execute("SELECT * FROM tb_notas_geo_uf LIMIT 5").fetchdf()
            print(df)
            
            print("\nYears present:")
            years = con.execute("SELECT DISTINCT ANO FROM tb_notas_geo_uf ORDER BY ANO").fetchall()
            print(years)
    else:
        print("Table tb_notas_geo_uf NOT found.")

except Exception as e:
    print(f"Error: {e}")
