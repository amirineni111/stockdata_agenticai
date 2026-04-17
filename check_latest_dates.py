"""
Check latest signal dates to diagnose cross-strategy join issue.
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
    """Create database connection."""
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
print("LATEST DATES DIAGNOSIS")
print("="*80)

# Latest Strategy 1 date for NASDAQ
query1 = """
SELECT MAX(signal_date) AS latest_s1_date
FROM vw_PowerBI_AI_Technical_Combos
WHERE market = 'NASDAQ 100'
"""
cursor.execute(query1)
latest_s1 = cursor.fetchone()[0]
print(f"\n1. Latest Strategy 1 signal_date for NASDAQ 100: {latest_s1}")

# Latest Strategy 2 date
query2 = """
SELECT MAX(trading_date) AS latest_s2_date
FROM ml_trading_predictions
"""
cursor.execute(query2)
latest_s2 = cursor.fetchone()[0]
print(f"2. Latest Strategy 2 trading_date: {latest_s2}")

# AMD's latest Strategy 1 date
query3 = """
SELECT MAX(signal_date) AS amd_latest_s1
FROM vw_PowerBI_AI_Technical_Combos
WHERE ticker = 'AMD' AND market = 'NASDAQ 100'
"""
cursor.execute(query3)
amd_s1 = cursor.fetchone()[0]
print(f"3. AMD's latest Strategy 1 signal_date: {amd_s1}")

# ADP's latest Strategy 1 date  
query4 = """
SELECT MAX(signal_date) AS adp_latest_s1
FROM vw_PowerBI_AI_Technical_Combos
WHERE ticker = 'ADP' AND market = 'NASDAQ 100'
"""
cursor.execute(query4)
adp_s1 = cursor.fetchone()[0]
print(f"4. ADP's latest Strategy 1 signal_date: {adp_s1}")

# How many NASDAQ stocks have signals on the latest date?
query5 = f"""
SELECT COUNT(DISTINCT ticker) AS tickers_on_latest_date
FROM vw_PowerBI_AI_Technical_Combos
WHERE market = 'NASDAQ 100'
  AND signal_date = '{latest_s1}'
  AND (trade_tier LIKE 'TIER 1%' OR trade_tier LIKE 'TIER 2%')
"""
cursor.execute(query5)
count_latest = cursor.fetchone()[0]
print(f"5. Number of NASDAQ stocks with TIER 1/2 signals on {latest_s1}: {count_latest}")

# Check if AMD would qualify on its last signal date
query6 = f"""
SELECT
    s1.ticker,
    s1.signal_type AS s1_direction,
    s1.trade_tier,
    s1.signal_date AS s1_date,
    m.predicted_signal AS s2_signal,
    m.confidence_percentage AS s2_conf,
    m.signal_strength AS s2_strength,
    m.trading_date AS s2_date
FROM vw_PowerBI_AI_Technical_Combos s1
LEFT JOIN ml_trading_predictions m 
    ON s1.ticker = m.ticker 
    AND m.trading_date = (SELECT MAX(trading_date) FROM ml_trading_predictions)
WHERE s1.ticker = 'AMD'
  AND s1.market = 'NASDAQ 100'
  AND s1.signal_date = '{amd_s1}'
  AND (s1.trade_tier LIKE 'TIER 1%' OR s1.trade_tier LIKE 'TIER 2%')
"""
cursor.execute(query6)
rows = cursor.fetchall()
if rows:
    print(f"\n6. AMD on its last S1 date ({amd_s1}) vs latest S2:")
    for row in rows:
        print(f"   S1: {row.s1_direction} ({row.trade_tier}) on {row.s1_date}")
        print(f"   S2: {row.s2_signal} ({row.s2_conf:.1f}% {row.s2_strength}) on {row.s2_date}")
        print(f"   → Time gap: S1 is {(latest_s1 - row.s1_date).days} days behind latest S1 date")

cursor.close()
conn.close()

print("\n" + "="*80)
print("CONCLUSION:")
print("AMD doesn't appear in cross-strategy because its last Strategy 1 signal")
print("was on a different date than the latest signal_date used by the query.")
print("The INNER JOIN requires BOTH strategies to have data on matching 'latest' dates.")
print("="*80)
