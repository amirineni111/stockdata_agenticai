"""
Debug NSE cross-strategy query to find the join issue.
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

print("="*100)
print("DEBUGGING NSE CROSS-STRATEGY QUERY")
print("="*100)

# Check sample tickers from NSE ML
print("\n1. Sample tickers from ml_nse_trading_predictions (latest date):")
query = """
SELECT TOP 5 ticker, predicted_signal, confidence_percentage, signal_strength,
       CAST(close_price AS FLOAT) AS price, trading_date
FROM ml_nse_trading_predictions
WHERE trading_date = (SELECT MAX(trading_date) FROM ml_nse_trading_predictions)
  AND signal_strength IN ('Strong', 'Moderate')
  AND confidence_percentage >= 55
  AND CAST(close_price AS FLOAT) >= 20
ORDER BY confidence_percentage DESC
"""
cursor.execute(query)
rows = cursor.fetchall()
sample_tickers_ml = []
for row in rows:
    print(f"  {row.ticker}: {row.predicted_signal} ({row.confidence_percentage}% {row.signal_strength}) @ ₹{row.price} on {row.trading_date}")
    sample_tickers_ml.append(row.ticker)

# Check if those same tickers exist in AI predictions
print("\n2. Checking if those tickers have AI predictions (days_ahead=3):")
if sample_tickers_ml:
    placeholders = ','.join(['?' for _ in sample_tickers_ml])
    query = f"""
    SELECT ai.ticker, ai.predicted_price, ai.prediction_date,
           ai.model_name, ai.days_ahead
    FROM ai_prediction_history ai
    WHERE ai.ticker IN ({placeholders})
      AND ai.days_ahead = 3
      AND ai.model_name = 'Ensemble'
      AND ai.prediction_date = (
          SELECT MAX(prediction_date) 
          FROM ai_prediction_history 
          WHERE days_ahead = 3
      )
    """
    cursor.execute(query, sample_tickers_ml)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"  {row.ticker}: Pred ₹{row.predicted_price:.2f} on {row.prediction_date}")
    else:
        print("  ❌ NONE of these tickers found in ai_prediction_history!")
        
        # Check what NSE tickers ARE in ai_prediction_history
        print("\n3. Sample NSE tickers that ARE in ai_prediction_history:")
        query = """
        SELECT TOP 5 ai.ticker, ai.predicted_price, ai.prediction_date
        FROM ai_prediction_history ai
        INNER JOIN nse_500 nse ON ai.ticker = nse.ticker
        WHERE ai.days_ahead = 3
          AND ai.model_name = 'Ensemble'
          AND ai.prediction_date = (
              SELECT MAX(prediction_date) 
              FROM ai_prediction_history 
              WHERE days_ahead = 3
          )
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        ai_tickers = []
        for row in rows:
            print(f"  {row.ticker}: Pred ₹{row.predicted_price:.2f} on {row.prediction_date}")
            ai_tickers.append(row.ticker)
        
        # Check if THOSE tickers have ML predictions
        if ai_tickers:
            print("\n4. Checking if those AI tickers have ML predictions:")
            placeholders = ','.join(['?' for _ in ai_tickers])
            query = f"""
            SELECT ticker, predicted_signal, confidence_percentage, trading_date
            FROM ml_nse_trading_predictions
            WHERE ticker IN ({placeholders})
              AND trading_date = (SELECT MAX(trading_date) FROM ml_nse_trading_predictions)
            """
            cursor.execute(query, ai_tickers)
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    print(f"  {row.ticker}: {row.predicted_signal} ({row.confidence_percentage}%) on {row.trading_date}")
            else:
                print("  ❌ NONE of these AI tickers found in ml_nse_trading_predictions!")

# Check latest dates
print("\n5. Checking latest dates in both tables:")
cursor.execute("SELECT MAX(trading_date) FROM ml_nse_trading_predictions")
ml_date = cursor.fetchone()[0]
print(f"  ml_nse_trading_predictions latest: {ml_date}")

cursor.execute("SELECT MAX(prediction_date) FROM ai_prediction_history WHERE days_ahead=3")
ai_date = cursor.fetchone()[0]
print(f"  ai_prediction_history latest (days_ahead=3): {ai_date}")

if ml_date != ai_date:
    print(f"\n  ⚠️  DATE MISMATCH: ML date ({ml_date}) != AI date ({ai_date})")
    print(f"  The join on prediction_date = trading_date will FAIL!")

cursor.close()
conn.close()

print("\n" + "="*100)
