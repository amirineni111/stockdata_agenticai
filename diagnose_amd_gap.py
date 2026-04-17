"""
Diagnose AMD data gap between Strategy 1 and Strategy 2.
Check underlying tables/views for both strategies.
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

print("="*100)
print("AMD DATA SOURCE ANALYSIS")
print("="*100)

# ============================================================================
# STRATEGY 1 SOURCES
# ============================================================================
print("\n" + "="*100)
print("STRATEGY 1: AI + Technical Combos")
print("Source: vw_PowerBI_AI_Technical_Combos (which combines 2 underlying tables)")
print("="*100)

# Check the view definition first
print("\n1. Checking latest data in vw_PowerBI_AI_Technical_Combos for AMD:")
print("-"*100)
query = """
SELECT TOP 10
    signal_date,
    ticker,
    company_name,
    signal_type,
    trade_tier,
    ROUND(CAST(ai_prediction_pct AS FLOAT), 2) AS ai_prediction_pct,
    technical_combo,
    signal_price
FROM vw_PowerBI_AI_Technical_Combos
WHERE ticker = 'AMD'
  AND market = 'NASDAQ 100'
ORDER BY signal_date DESC
"""
cursor.execute(query)
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  {row.signal_date} | {row.signal_type:8} | {row.trade_tier:35} | AI: {row.ai_prediction_pct:6}% | {row.technical_combo}")
    latest_s1_date = rows[0].signal_date
    print(f"\n  → Latest Strategy 1 signal: {latest_s1_date}")
else:
    print("  NO RESULTS")
    latest_s1_date = None

# Check underlying table 1: ai_prediction_history
print("\n2. Checking ai_prediction_history (AI price predictions) for AMD:")
print("-"*100)
query = """
SELECT TOP 10
    prediction_date,
    ticker,
    model_name,
    predicted_price,
    actual_price,
    direction_correct,
    percentage_error
FROM ai_prediction_history
WHERE ticker = 'AMD'
ORDER BY prediction_date DESC
"""
cursor.execute(query)
rows = cursor.fetchall()
if rows:
    for row in rows:
        pred_price = f"${row.predicted_price:7.2f}" if row.predicted_price else "N/A"
        actual_price = f"${row.actual_price:7.2f}" if row.actual_price else "N/A"
        direction = str(row.direction_correct) if row.direction_correct is not None else "N/A"
        print(f"  {row.prediction_date} | {row.model_name:15} | Pred: {pred_price:>10} | Actual: {actual_price:>10} | Correct: {direction}")
    latest_ai_pred = rows[0].prediction_date
    print(f"\n  → Latest AI prediction: {latest_ai_pred}")
else:
    print("  NO RESULTS")
    latest_ai_pred = None

# Check underlying table 2: signal_tracking_history
print("\n3. Checking signal_tracking_history (Technical indicators) for AMD:")
print("-"*100)
query = """
SELECT TOP 10
    signal_date,
    ticker,
    signal_type,
    signal_strength,
    result_7d,
    result_14d,
    actual_change_7d
FROM signal_tracking_history
WHERE ticker = 'AMD'
  AND market = 'NASDAQ 100'
ORDER BY signal_date DESC
"""
cursor.execute(query)
rows = cursor.fetchall()
if rows:
    for row in rows:
        strength = row.signal_strength or 'N/A'
        result_7d = row.result_7d or 'N/A'
        result_14d = row.result_14d or 'N/A'
        change_7d = f"{row.actual_change_7d:+6.2f}%" if row.actual_change_7d is not None else "N/A"
        print(f"  {row.signal_date} | {row.signal_type:8} | {strength:12} | 7d: {result_7d:8} | 14d: {result_14d:8}")
    latest_tech_signal = rows[0].signal_date
    print(f"\n  → Latest technical signal: {latest_tech_signal}")
else:
    print("  NO RESULTS")
    latest_tech_signal = None

# ============================================================================
# STRATEGY 2 SOURCES
# ============================================================================
print("\n" + "="*100)
print("STRATEGY 2: ML Classifier + RSI Alignment")
print("Source: ml_trading_predictions (from sqlserver_copilot ML pipeline)")
print("="*100)

print("\n4. Checking ml_trading_predictions (ML classifier) for AMD:")
print("-"*100)
query = """
SELECT TOP 10
    trading_date,
    ticker,
    predicted_signal,
    confidence_percentage,
    signal_strength,
    RSI,
    rsi_category,
    CAST(close_price AS FLOAT) AS close_price
FROM ml_trading_predictions
WHERE ticker = 'AMD'
ORDER BY trading_date DESC
"""
cursor.execute(query)
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  {row.trading_date} | {row.predicted_signal:4} | Conf: {row.confidence_percentage:5.1f}% | {row.signal_strength:8} | RSI: {row.RSI:5.1f} ({row.rsi_category:12}) | ${row.close_price:7.2f}")
    latest_s2_date = rows[0].trading_date
    print(f"\n  → Latest Strategy 2 prediction: {latest_s2_date}")
else:
    print("  NO RESULTS")
    latest_s2_date = None

# ============================================================================
# GAP ANALYSIS
# ============================================================================
print("\n" + "="*100)
print("GAP ANALYSIS")
print("="*100)

if latest_s1_date and latest_s2_date:
    gap_days = (latest_s2_date - latest_s1_date).days
    print(f"\n  Strategy 1 latest: {latest_s1_date}")
    print(f"  Strategy 2 latest: {latest_s2_date}")
    print(f"  → TIME GAP: {gap_days} days")
    
    if gap_days > 0:
        print(f"\n  ⚠️  PROBLEM: Strategy 1 is {gap_days} days behind Strategy 2")
        print(f"  ⚠️  This causes AMD to be excluded from cross-strategy analysis")
        
        # Check if we have raw price data for AMD on recent dates
        print(f"\n5. Checking nasdaq_100_hist_data (raw price data source) for AMD:")
        print("-"*100)
        query = """
        SELECT TOP 10
            trading_date,
            ticker,
            CAST(close_price AS FLOAT) AS close_price,
            CAST(volume AS BIGINT) AS volume
        FROM nasdaq_100_hist_data
        WHERE ticker = 'AMD'
        ORDER BY trading_date DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print(f"  {row.trading_date} | ${row.close_price:7.2f} | Vol: {row.volume:,}")
            latest_raw_data = rows[0].trading_date
            print(f"\n  → Latest raw price data: {latest_raw_data}")
            
            if latest_raw_data == latest_s2_date:
                print(f"\n  ✓ Raw price data is CURRENT (matches Strategy 2)")
            
            if latest_raw_data > latest_s1_date:
                print(f"\n  ⚠️  Raw data exists for {(latest_raw_data - latest_s1_date).days} days AFTER last Strategy 1 signal")
                print(f"  ⚠️  This suggests Strategy 1 pipeline (streamlit-trading-dashboard) is not processing AMD")
        else:
            print("  NO RAW DATA FOUND")

print("\n" + "="*100)
print("CONCLUSION:")
print("="*100)
print("""
Strategy 1 uses: vw_PowerBI_AI_Technical_Combos
  └─ Combines: ai_prediction_history + signal_tracking_history
  └─ Populated by: streamlit-trading-dashboard (6:00 PM & 7:00 PM jobs)

Strategy 2 uses: ml_trading_predictions
  └─ Populated by: sqlserver_copilot on ML Machine (6:00 AM daily)

If AMD has current Strategy 2 data but stale Strategy 1 data, the issue is in:
  → streamlit-trading-dashboard repo not generating AI predictions or technical signals for AMD
  → Possible causes:
    - AMD removed from prediction_watchlist table
    - Technical indicator calculations failing for AMD
    - AI model not running for AMD ticker
""")

cursor.close()
conn.close()

print("="*100)
