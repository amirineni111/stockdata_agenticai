"""
Check if ml_nse_trading_predictions table has data.
"""
import pyodbc
from config.settings import (
    SQL_SERVER,
    SQL_DATABASE,
    SQL_DRIVER,
    SQL_USERNAME,
    SQL_PASSWORD,
    SQL_TRUSTED_CONNECTION
)

def get_connection():
    if SQL_TRUSTED_CONNECTION.lower() == 'yes':
        conn_str = (
            f"DRIVER={SQL_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={SQL_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD};"
        )
    return pyodbc.connect(conn_str)

conn = get_connection()
cursor = conn.cursor()

print("="*80)
print("CHECKING ml_nse_trading_predictions TABLE")
print("="*80)

# Total count
query = "SELECT COUNT(*) AS cnt FROM ml_nse_trading_predictions"
cursor.execute(query)
total_count = cursor.fetchone().cnt
print(f"\nTotal rows: {total_count}")

# Latest date count
query = """
SELECT COUNT(*) AS cnt, MAX(trading_date) AS latest_date 
FROM ml_nse_trading_predictions
"""
cursor.execute(query)
row = cursor.fetchone()
print(f"Latest date: {row.latest_date}, rows on latest date: (checking...)")

# Count on latest date
query = """
SELECT COUNT(*) AS cnt
FROM ml_nse_trading_predictions
WHERE trading_date = (SELECT MAX(trading_date) FROM ml_nse_trading_predictions)
"""
cursor.execute(query)
latest_count = cursor.fetchone().cnt
print(f"Rows on latest date: {latest_count}")

# Sample records
print("\nSample records (any filters):")
query = """
SELECT TOP 10 ticker, trading_date, predicted_signal, confidence_percentage, 
       signal_strength, CAST(close_price AS FLOAT) AS price
FROM ml_nse_trading_predictions
WHERE trading_date = (SELECT MAX(trading_date) FROM ml_nse_trading_predictions)
ORDER BY confidence_percentage DESC
"""
cursor.execute(query)
rows = cursor.fetchall()
if rows:
    for row in rows:
        price_str = f"₹{row.price:.2f}" if row.price else "NULL"
        print(f"  {row.ticker}: {row.predicted_signal} ({row.confidence_percentage}% {row.signal_strength}) @ {price_str}")
else:
    print("  NO ROWS")

# Count with filters
print("\nRows matching Strategy 1 filters (Strong/Moderate, conf>=55, price>=20):")
query = """
SELECT COUNT(*) AS cnt
FROM ml_nse_trading_predictions
WHERE trading_date = (SELECT MAX(trading_date) FROM ml_nse_trading_predictions)
  AND signal_strength IN ('Strong', 'Moderate')
  AND confidence_percentage >= 55
  AND CAST(close_price AS FLOAT) >= 20
"""
cursor.execute(query)
filtered_count = cursor.fetchone().cnt
print(f"  Count: {filtered_count}")

cursor.close()
conn.close()

print("\n" + "="*80)
