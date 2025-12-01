import duckdb
from enem_project.config.settings import settings

db_path = settings.DATA_DIR / "enem.duckdb"
try:
    con = duckdb.connect(str(db_path), read_only=True)
    print("\n--- Check 2023 ---")
    df_race = con.execute("""
        SELECT 
            TP_COR_RACA,
            COUNT(*) as count
        FROM gold_classes
        WHERE ANO = 2023
        GROUP BY TP_COR_RACA
    """).fetchdf()
    print(df_race)
except Exception as e:
    print(e)
