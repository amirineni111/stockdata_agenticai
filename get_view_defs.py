import pyodbc
from config.settings import get_sql_connection_string

conn = pyodbc.connect(get_sql_connection_string())
cursor = conn.cursor()

views = [
    'vw_crossover_signals_Forex',
    'vw_crossover_signals_NASDAQ_100',
    'vw_crossover_signals_NSE_500'
]

for v in views:
    cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID(?))", v)
    row = cursor.fetchone()
    print(f'===== {v} =====')
    print(row[0] if row and row[0] else 'VIEW NOT FOUND')
    print()

conn.close()
