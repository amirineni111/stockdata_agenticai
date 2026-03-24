import pyodbc
from config.settings import get_sql_connection_string

conn = pyodbc.connect(get_sql_connection_string(), timeout=30)
cursor = conn.cursor()

# Check macd_signals views (not macd views) — these are what crossover views reference
for m in ['nasdaq_100', 'nse_500', 'forex']:
    vn = f'{m}_macd_signals'
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME = '{vn}' ORDER BY ORDINAL_POSITION"
    )
    cols = [r[0] for r in cursor.fetchall()]
    if cols:
        print(f"{vn}: {cols}")
    else:
        # Try as view
        cursor.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS "
            f"WHERE TABLE_NAME = '{vn}'"
        )
        exists = cursor.fetchone()
        print(f"{vn}: VIEW EXISTS={exists is not None}, COLUMNS=[] (may be broken)")

# Check crossover view definition to find FROM clause
print("\n--- Crossover Forex view FROM clauses ---")
cursor.execute(
    "SELECT definition FROM sys.sql_modules "
    "WHERE object_id = OBJECT_ID('vw_crossover_signals_Forex')"
)
row = cursor.fetchone()
if row:
    for line in row[0].split('\n'):
        stripped = line.strip().lower()
        if 'from ' in stripped or 'join ' in stripped:
            print(line.rstrip())

cursor.close()
conn.close()
