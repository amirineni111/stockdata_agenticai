"""
Quick diagnostic script to check AMD ticker in both strategies.
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

# Check Strategy 1 (AI + Technical Combos)
query_s1 = """
SELECT TOP 5
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
  AND (trade_tier LIKE 'TIER 1%' OR trade_tier LIKE 'TIER 2%')
ORDER BY signal_date DESC
"""

# Check Strategy 2 (ML Classifier)
query_s2 = """
SELECT TOP 5
    trading_date,
    ticker,
    predicted_signal,
    confidence_percentage,
    signal_strength,
    ROUND(RSI, 1) AS RSI,
    rsi_category,
    CAST(close_price AS FLOAT) AS close_price
FROM ml_trading_predictions
WHERE ticker = 'AMD'
ORDER BY trading_date DESC
"""

# Check what would show in cross-strategy (the exact WHERE clause)
query_cross = """
WITH s1_best AS (
    SELECT
        s1.market,
        s1.ticker,
        s1.company_name,
        s1.signal_type,
        s1.trade_tier,
        ROUND(CAST(s1.ai_prediction_pct AS FLOAT), 2) AS ai_prediction_pct,
        s1.technical_combo,
        ROW_NUMBER() OVER (
            PARTITION BY s1.ticker
            ORDER BY ABS(CAST(s1.ai_prediction_pct AS FLOAT)) DESC
        ) AS rn
    FROM vw_PowerBI_AI_Technical_Combos s1
    INNER JOIN (
        SELECT MAX(signal_date) AS max_date
        FROM vw_PowerBI_AI_Technical_Combos
        WHERE market = 'NASDAQ 100'
    ) latest ON s1.signal_date = latest.max_date
    WHERE s1.market = 'NASDAQ 100'
      AND (s1.trade_tier LIKE 'TIER 1%' OR s1.trade_tier LIKE 'TIER 2%')
      AND s1.signal_price > 15
      AND s1.ticker = 'AMD'
)
SELECT
    'NASDAQ 100' AS market,
    s1b.ticker,
    s1b.company_name AS company,
    s1b.signal_type AS s1_direction,
    s1b.trade_tier AS s1_tier,
    s1b.ai_prediction_pct AS s1_ai_pct,
    s1b.technical_combo AS s1_tech_combo,
    CASE
        WHEN m.predicted_signal IN ('Sell', 'SELL', 'Overbought') THEN 'Sell'
        WHEN m.predicted_signal IN ('Buy', 'BUY', 'Oversold') THEN 'Buy'
        ELSE m.predicted_signal
    END AS s2_signal,
    ROUND(m.confidence_percentage, 1) AS s2_confidence_pct,
    m.signal_strength AS s2_strength,
    ROUND(m.RSI, 1) AS s2_rsi,
    m.rsi_category AS s2_rsi_category,
    CASE
        WHEN (s1b.signal_type = 'BEARISH'
              AND m.predicted_signal IN ('Sell', 'SELL', 'Overbought'))
          OR (s1b.signal_type = 'BULLISH'
              AND m.predicted_signal IN ('Buy', 'BUY', 'Oversold'))
        THEN 'ALIGNED'
        ELSE 'CONFLICTING'
    END AS cross_strategy_agreement,
    -- Show WHY it's filtered
    CASE
        WHEN m.signal_strength NOT IN ('Strong', 'Moderate') THEN 'FILTERED: signal_strength=' + m.signal_strength
        WHEN m.confidence_percentage < 55 THEN 'FILTERED: confidence < 55%'
        WHEN CAST(m.close_price AS FLOAT) <= 15 THEN 'FILTERED: price <= 15'
        WHEN NOT (
            (s1b.signal_type = 'BEARISH'
             AND m.predicted_signal IN ('Sell', 'SELL', 'Overbought'))
          OR (s1b.signal_type = 'BULLISH'
             AND m.predicted_signal IN ('Buy', 'BUY', 'Oversold'))
        ) THEN 'FILTERED: NOT ALIGNED (conflicting directions)'
        ELSE 'PASSES ALL FILTERS'
    END AS filter_status
FROM ml_trading_predictions m
INNER JOIN (
    SELECT MAX(trading_date) AS max_date FROM ml_trading_predictions
) m_latest ON m.trading_date = m_latest.max_date
INNER JOIN s1_best s1b ON m.ticker = s1b.ticker AND s1b.rn = 1
WHERE m.ticker = 'AMD'
"""

print("="*80)
print("CHECKING AMD TICKER IN BOTH STRATEGIES")
print("="*80)

conn = get_connection()
cursor = conn.cursor()

print("\n1. STRATEGY 1 (AI + Technical Combos) - Last 5 signals:")
print("-" * 80)
cursor.execute(query_s1)
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"Date: {row.signal_date}, Direction: {row.signal_type}, Tier: {row.trade_tier}, "
              f"AI%: {row.ai_prediction_pct}, Combo: {row.technical_combo}, Price: ${row.signal_price}")
else:
    print("NO RESULTS FOUND")

print("\n2. STRATEGY 2 (ML Classifier) - Last 5 predictions:")
print("-" * 80)
cursor.execute(query_s2)
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"Date: {row.trading_date}, Signal: {row.predicted_signal}, "
              f"Confidence: {row.confidence_percentage:.1f}%, Strength: {row.signal_strength}, "
              f"RSI: {row.RSI}, Category: {row.rsi_category}, Price: ${row.close_price:.2f}")
else:
    print("NO RESULTS FOUND")

print("\n3. CROSS-STRATEGY CHECK (with filter diagnosis):")
print("-" * 80)
cursor.execute(query_cross)
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"\nS1 Direction: {row.s1_direction}, S1 Tier: {row.s1_tier}, S1 AI%: {row.s1_ai_pct}")
        print(f"S2 Signal: {row.s2_signal}, S2 Confidence: {row.s2_confidence_pct}%, S2 Strength: {row.s2_strength}")
        print(f"S2 RSI: {row.s2_rsi} ({row.s2_rsi_category})")
        print(f"Agreement: {row.cross_strategy_agreement}")
        print(f"Filter Status: {row.filter_status}")
else:
    print("NO RESULTS - AMD not in latest cross-strategy join")

cursor.close()
conn.close()

print("\n" + "="*80)
