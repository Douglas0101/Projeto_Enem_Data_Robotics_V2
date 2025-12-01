import duckdb
from enem_project.config.settings import settings

db_path = settings.DATA_DIR / "enem.duckdb"
print(f"Connecting to {db_path}")

try:
    con = duckdb.connect(str(db_path), read_only=True)
    
    # Simulate the query for SP
    uf = 'SP'
    sql = """
        SELECT *
        FROM tb_notas_geo_uf
        WHERE INSCRITOS >= 0 AND SG_UF_PROVA = ?
        ORDER BY ANO, SG_UF_PROVA
    """
    
    print(f"\n--- Querying for UF: {uf} ---")
    df = con.execute(sql, [uf]).fetchdf()
    
    if df.empty:
        print("No data found for UF=SP")
    else:
        print(f"Found {len(df)} rows.")
        print(df[['ANO', 'SG_UF_PROVA', 'NOTA_MATEMATICA_mean']].head())
        print("Years:", df['ANO'].unique())

except Exception as e:
    print(f"Error: {e}")
