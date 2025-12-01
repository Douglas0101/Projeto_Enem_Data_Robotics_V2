import duckdb
from enem_project.config.settings import settings
import pandas as pd

db_path = settings.DATA_DIR / "enem.duckdb"
print(f"Connecting to {db_path}")

try:
    con = duckdb.connect(str(db_path), read_only=True)
    
    tables = con.execute("SHOW TABLES").fetchall()
    print("Tables:", tables)
    
    if ('gold_classes',) in tables:
        print("\n--- gold_classes found ---")
        count = con.execute("SELECT COUNT(*) FROM gold_classes").fetchone()[0]
        print(f"Total rows: {count}")
        
        if count > 0:
            print("\n--- Distinct Years in gold_classes ---")
            years = con.execute("SELECT DISTINCT ANO FROM gold_classes ORDER BY ANO").fetchall()
            print(years)
            
            print("\n--- Sample Data (First 5 rows) ---")
            df = con.execute("SELECT * FROM gold_classes LIMIT 5").fetchdf()
            print(df)
            
            # Check for specific year 2023 (or 2022) logic
            print("\n--- Check 2009 (User mentioned 2009) ---")
            count_2009 = con.execute("SELECT COUNT(*) FROM gold_classes WHERE ANO = 2009").fetchone()[0]
            print(f"Rows for 2009: {count_2009}")
            
            if count_2009 > 0:
                 print("\n--- Group By Race for 2009 ---")
                 df_race = con.execute("""
                    SELECT 
                        TP_COR_RACA,
                        COUNT(*) as count,
                        AVG(NOTA_MATEMATICA) as avg_mat
                    FROM gold_classes
                    WHERE ANO = 2009
                    GROUP BY TP_COR_RACA
                 """).fetchdf()
                 print(df_race)

    else:
        print("gold_classes table NOT found.")
        
        # Check if we can generate it or if we should use silver_microdados
        if ('silver_microdados',) in tables:
             print("\n--- silver_microdados found (fallback source?) ---")
             count_silver = con.execute("SELECT COUNT(*) FROM silver_microdados").fetchone()[0]
             print(f"Total rows in silver: {count_silver}")

except Exception as e:
    print(f"Error: {e}")
