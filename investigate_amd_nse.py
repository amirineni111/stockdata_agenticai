"""
Check if AMD is in the full ALIGNED list and investigate NSE issue.
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
print("DETAILED INVESTIGATION")
print("="*100)

# Check if AMD is in the FULL NASDAQ cross-strategy list (remove TOP 15 limit)
print("\n1. Checking if AMD is in the FULL NASDAQ ALIGNED list:")
print("-"*100)

query_amd = """
WITH s1_ml AS (
    SELECT
        ml.ticker,
        nasdaq.company_name,
        ml.predicted_signal,
        ROUND(ml.confidence_percentage, 1) AS ml_confidence_pct,
        ml.signal_strength,
        ROUND(ml.RSI, 1) AS rsi_value,
        ml.rsi_category,
        CAST(ml.close_price AS FLOAT) AS current_price,
        ml.trading_date
    FROM ml_trading_predictions ml
    INNER JOIN nasdaq_top100 nasdaq ON ml.ticker = nasdaq.ticker
    INNER JOIN (
        SELECT MAX(trading_date) AS max_date FROM ml_trading_predictions
    ) latest ON ml.trading_date = latest.max_date
    WHERE ml.signal_strength IN ('Strong', 'Moderate')
      AND ml.confidence_percentage >= 55
      AND CAST(ml.close_price AS FLOAT) > 15
),
s2_ai AS (
    SELECT
        ai.ticker,
        ai.model_name,
        ai.predicted_price,
        ai.prediction_date,
        CAST(hist.close_price AS FLOAT) AS current_price,
        CASE
            WHEN ai.predicted_price > CAST(hist.close_price AS FLOAT) THEN 'BULLISH'
            WHEN ai.predicted_price < CAST(hist.close_price AS FLOAT) THEN 'BEARISH'
            ELSE 'NEUTRAL'
        END AS ai_direction,
        ROUND(
            ((ai.predicted_price - CAST(hist.close_price AS FLOAT)) 
            / NULLIF(CAST(hist.close_price AS FLOAT), 0)) * 100, 2
        ) AS ai_change_pct
    FROM ai_prediction_history ai
    INNER JOIN nasdaq_100_hist_data hist 
        ON ai.ticker = hist.ticker 
        AND ai.prediction_date = hist.trading_date
    INNER JOIN (
        SELECT MAX(prediction_date) AS max_date 
        FROM ai_prediction_history 
        WHERE days_ahead = 3
    ) latest ON ai.prediction_date = latest.max_date
    WHERE ai.days_ahead = 3
      AND ai.model_name = 'Ensemble'
)
SELECT
    s1.ticker,
    s1.company_name,
    s1.predicted_signal AS s1_ml_signal,
    s1.ml_confidence_pct,
    s1.signal_strength,
    s2.ai_direction,
    s2.ai_change_pct,
    s2.predicted_price AS s2_target_price,
    s1.current_price,
    CASE
        WHEN (s1.predicted_signal IN ('Buy', 'BUY') AND s2.ai_direction = 'BULLISH')
          OR (s1.predicted_signal IN ('Sell', 'SELL') AND s2.ai_direction = 'BEARISH')
        THEN 'ALIGNED'
        ELSE 'CONFLICTING'
    END AS cross_strategy_agreement
FROM s1_ml s1
INNER JOIN s2_ai s2 ON s1.ticker = s2.ticker
WHERE s1.ticker = 'AMD'
"""

cursor.execute(query_amd)
rows = cursor.fetchall()

if rows:
    for row in rows:
        print(f"✓ AMD FOUND in cross-strategy!")
        print(f"  S1 ML Signal: {row.s1_ml_signal}")
        print(f"  S1 Confidence: {row.ml_confidence_pct}%")
        print(f"  S1 Strength: {row.signal_strength}")
        print(f"  S2 AI Direction: {row.ai_direction}")
        print(f"  S2 Predicted Change: {row.ai_change_pct}%")
        print(f"  S2 Target Price: ${row.s2_target_price:.2f}")
        print(f"  Current Price: ${row.current_price:.2f}")
        print(f"  Agreement: {row.cross_strategy_agreement}")
else:
    print("❌ AMD NOT FOUND - checking why...")
    
    # Check if AMD is in Strategy 1 (ML predictions)
    print("\n  Checking if AMD is in Strategy 1 (ml_trading_predictions):")
    query = """
    SELECT ticker, predicted_signal, confidence_percentage, signal_strength, 
           CAST(close_price AS FLOAT) AS price
    FROM ml_trading_predictions
    WHERE ticker = 'AMD'
      AND trading_date = (SELECT MAX(trading_date) FROM ml_trading_predictions)
    """
    cursor.execute(query)
    row = cursor.fetchone()
    if row:
        print(f"    ✓ Found: {row.predicted_signal} ({row.confidence_percentage}% {row.signal_strength}) @ ${row.price}")
        if row.price <= 15:
            print(f"    ❌ FILTERED OUT: price ${row.price} <= $15 threshold")
        if row.confidence_percentage < 55:
            print(f"    ❌ FILTERED OUT: confidence {row.confidence_percentage}% < 55% threshold")
        if row.signal_strength not in ('Strong', 'Moderate'):
            print(f"    ❌ FILTERED OUT: strength '{row.signal_strength}' not in ('Strong', 'Moderate')")
    else:
        print("    ❌ NOT FOUND in ml_trading_predictions")
    
    # Check if AMD is in Strategy 2 (AI predictions)
    print("\n  Checking if AMD is in Strategy 2 (ai_prediction_history with days_ahead=3):")
    query = """
    SELECT ai.ticker, ai.predicted_price, ai.prediction_date, 
           CAST(hist.close_price AS FLOAT) AS current_price
    FROM ai_prediction_history ai
    INNER JOIN nasdaq_100_hist_data hist 
        ON ai.ticker = hist.ticker 
        AND ai.prediction_date = hist.trading_date
    WHERE ai.ticker = 'AMD'
      AND ai.days_ahead = 3
      AND ai.model_name = 'Ensemble'
      AND ai.prediction_date = (
          SELECT MAX(prediction_date) 
          FROM ai_prediction_history 
          WHERE days_ahead = 3
      )
    """
    cursor.execute(query)
    row = cursor.fetchone()
    if row:
        direction = 'BULLISH' if row.predicted_price > row.current_price else 'BEARISH'
        change_pct = ((row.predicted_price - row.current_price) / row.current_price) * 100
        print(f"    ✓ Found: Pred ${row.predicted_price:.2f} vs Current ${row.current_price:.2f} = {direction} ({change_pct:+.2f}%)")
        print(f"    Date: {row.prediction_date}")
    else:
        print("    ❌ NOT FOUND in ai_prediction_history with days_ahead=3 and model_name='Ensemble'")

# Check why NSE has no results
print("\n2. Investigating why NSE has NO RESULTS:")
print("-"*100)

# Check if we have NSE ML predictions
query = "SELECT COUNT(*) AS cnt FROM ml_nse_trading_predictions WHERE trading_date = (SELECT MAX(trading_date) FROM ml_nse_trading_predictions)"
cursor.execute(query)
nse_ml_count = cursor.fetchone().cnt
print(f"  NSE ML predictions (latest date): {nse_ml_count} rows")

# Check if we have NSE AI predictions with days_ahead=3
query = """
SELECT COUNT(*) AS cnt 
FROM ai_prediction_history ai
WHERE ai.days_ahead = 3
  AND ai.model_name = 'Ensemble'
  AND ai.prediction_date = (SELECT MAX(prediction_date) FROM ai_prediction_history WHERE days_ahead = 3)
  AND EXISTS (SELECT 1 FROM nse_500 WHERE ticker = ai.ticker)
"""
cursor.execute(query)
nse_ai_count = cursor.fetchone().cnt
print(f"  NSE AI predictions (days_ahead=3, latest date): {nse_ai_count} rows")

if nse_ai_count == 0:
    print("\n  ⚠️  ISSUE: No ai_prediction_history entries for NSE tickers with days_ahead=3!")
    print("  This table might only have NASDAQ tickers or different days_ahead values.")

# Check what markets/days_ahead are in ai_prediction_history
query = """
SELECT DISTINCT days_ahead, COUNT(DISTINCT ticker) AS ticker_count
FROM ai_prediction_history
WHERE prediction_date = (SELECT MAX(prediction_date) FROM ai_prediction_history)
GROUP BY days_ahead
ORDER BY days_ahead
"""
cursor.execute(query)
rows = cursor.fetchall()
print("\n  ai_prediction_history breakdown by days_ahead (latest date):")
for row in rows:
    print(f"    days_ahead={row.days_ahead}: {row.ticker_count} unique tickers")

cursor.close()
conn.close()

print("\n" + "="*100)
