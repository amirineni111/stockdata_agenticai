"""
Test the new cross-strategy queries to verify AMD appears.
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
from config.sql_queries import CROSS_STRATEGY_QUERIES

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
print("TESTING NEW CROSS-STRATEGY QUERIES")
print("="*100)

# Test NASDAQ query
print("\n1. Testing NASDAQ Cross-Strategy Query:")
print("-"*100)
try:
    cursor.execute(CROSS_STRATEGY_QUERIES["common_stocks_nasdaq"])
    rows = cursor.fetchall()
    
    if rows:
        print(f"\nFound {len(rows)} ALIGNED stocks\n")
        amd_found = False
        
        for row in rows:
            if row.ticker == 'AMD':
                amd_found = True
                print(f"✓ AMD FOUND!")
                print(f"  Ticker: {row.ticker}")
                print(f"  Company: {row.company_name}")
                print(f"  S1 ML Signal: {row.s1_ml_signal}")
                print(f"  S1 Confidence: {row.s1_confidence_pct}%")
                print(f"  S1 Strength: {row.s1_strength}")
                print(f"  S1 RSI: {row.rsi_value} ({row.rsi_category})")
                print(f"  S2 AI Direction: {row.s2_ai_direction}")
                print(f"  S2 Predicted Change: {row.s2_predicted_change_pct}%")
                print(f"  S2 Target Price: ${row.s2_target_price:.2f}")
                print(f"  Current Price: ${row.current_price:.2f}")
                print(f"  Agreement: {row.cross_strategy_agreement}")
                print()
        
        if not amd_found:
            print("\n⚠️  AMD NOT in results. Showing first 5 stocks:")
            for i, row in enumerate(rows[:5], 1):
                print(f"\n{i}. {row.ticker} ({row.company_name})")
                print(f"   S1: {row.s1_ml_signal} ({row.s1_confidence_pct}% {row.s1_strength})")
                print(f"   S2: {row.s2_ai_direction} ({row.s2_predicted_change_pct:+.2f}%)")
                print(f"   Agreement: {row.cross_strategy_agreement}")
    else:
        print("\n⚠️  NO RESULTS from query")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")

# Test NASDAQ summary
print("\n2. Testing NASDAQ Summary Query:")
print("-"*100)
try:
    cursor.execute(CROSS_STRATEGY_QUERIES["common_stocks_nasdaq_summary"])
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            print(f"  {row.cross_agreement}: {row.total_stocks} stocks (avg ML confidence: {row.avg_ml_confidence}%)")
    else:
        print("  NO RESULTS")
        
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test NSE query
print("\n3. Testing NSE Cross-Strategy Query:")
print("-"*100)
try:
    cursor.execute(CROSS_STRATEGY_QUERIES["common_stocks_both_strategies"])
    rows = cursor.fetchall()
    
    if rows:
        print(f"\nFound {len(rows)} ALIGNED NSE stocks")
        print("\nFirst 5 stocks:")
        for i, row in enumerate(rows[:5], 1):
            print(f"\n{i}. {row.ticker} ({row.company_name})")
            print(f"   S1: {row.s1_ml_signal} ({row.s1_confidence_pct}% {row.s1_strength})")
            print(f"   S2: {row.s2_ai_direction} ({row.s2_predicted_change_pct:+.2f}%)")
            print(f"   Current: ₹{row.current_price:.2f}, Target: ₹{row.s2_target_price:.2f}")
    else:
        print("  NO RESULTS")
        
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test NSE summary
print("\n4. Testing NSE Summary Query:")
print("-"*100)
try:
    cursor.execute(CROSS_STRATEGY_QUERIES["common_stocks_summary"])
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            print(f"  {row.cross_agreement}: {row.total_stocks} stocks (avg ML confidence: {row.avg_ml_confidence}%)")
    else:
        print("  NO RESULTS")
        
except Exception as e:
    print(f"❌ ERROR: {e}")

cursor.close()
conn.close()

print("\n" + "="*100)
print("TEST COMPLETE")
print("="*100)
