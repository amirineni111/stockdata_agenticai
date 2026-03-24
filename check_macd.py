import pyodbc
from config.settings import get_sql_connection_string

conn = pyodbc.connect(get_sql_connection_string(), timeout=30)
cursor = conn.cursor()

# 1. MACD view columns for all markets
for m in ['nasdaq_100', 'nse_500', 'Forex']:
    vn = m + '_macd'
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME = '{vn}' ORDER BY ORDINAL_POSITION"
    )
    cols = [r[0] for r in cursor.fetchall()]
    print(f"{vn}: {cols}")

# 2. Check what crossover view expects (look for MACD_Signal)
print("\n--- Crossover view MACD references ---")
cursor.execute(
    "SELECT definition FROM sys.sql_modules "
    "WHERE object_id = OBJECT_ID('vw_crossover_signals_Forex')"
)
row = cursor.fetchone()
if row:
    for line in row[0].split('\n'):
        if 'macd' in line.lower():
            print(line.rstrip())

# 3. Test forex agent queries individually
print("\n--- Testing forex_crossover_signals query ---")
from config.sql_queries import FOREX_QUERIES
try:
    cursor.execute(FOREX_QUERIES['forex_crossover_signals'])
    rows = cursor.fetchall()
    print(f"OK: {len(rows)} rows")
except Exception as e:
    print(f"FAIL: {str(e)[:200]}")

cursor.close()
conn.close()
