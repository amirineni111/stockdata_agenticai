"""Test all SMA-dependent views and agent queries after SMA column changes."""
import pyodbc
import time
from config.settings import get_sql_connection_string

conn = pyodbc.connect(get_sql_connection_string(), timeout=30)
cursor = conn.cursor()

# ============================================================
# PART 1: Test SMA/EMA views directly
# ============================================================
print("=" * 70)
print("PART 1: TESTING SMA/EMA VIEWS DIRECTLY")
print("=" * 70)

sma_views = [
    "nasdaq_100_ema_sma_view",
    "nse_500_ema_sma_view",
    "forex_ema_sma_view",
    "nasdaq_100_sma_signals",
    "nse_500_sma_signals",
    "forex_sma_signals",
]

for view in sma_views:
    try:
        cursor.execute(f"SELECT TOP 1 * FROM [{view}]")
        cols = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        print(f"  OK  {view} — columns: {cols}")
    except Exception as e:
        print(f"  FAIL {view} — {e}")

# ============================================================
# PART 2: Test Bollinger Band views (use SMA_20)
# ============================================================
print("\n" + "=" * 70)
print("PART 2: TESTING BOLLINGER BAND VIEWS (reference SMA_20)")
print("=" * 70)

bb_views = [
    "nasdaq_100_bollingerband",
    "nse_500_bollingerband",
    "Forex_bollingerband",
]

for view in bb_views:
    try:
        cursor.execute(f"SELECT TOP 1 * FROM [{view}]")
        cols = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        has_sma20 = "SMA_20" in cols
        print(f"  OK  {view} — has SMA_20: {has_sma20} — columns: {cols}")
    except Exception as e:
        print(f"  FAIL {view} — {e}")

# ============================================================
# PART 3: Test Crossover Signal views (depend on SMA views)
# ============================================================
print("\n" + "=" * 70)
print("PART 3: TESTING CROSSOVER SIGNAL VIEWS")
print("=" * 70)

crossover_views = [
    "vw_crossover_signals_NASDAQ_100",
    "vw_crossover_signals_NSE_500",
    "vw_crossover_signals_Forex",
]

for view in crossover_views:
    try:
        cursor.execute(f"SELECT TOP 1 * FROM [{view}]")
        cols = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        print(f"  OK  {view} — columns: {cols}")
    except Exception as e:
        print(f"  FAIL {view} — {e}")

# ============================================================
# PART 4: Test Support/Resistance views
# ============================================================
print("\n" + "=" * 70)
print("PART 4: TESTING SUPPORT/RESISTANCE VIEWS")
print("=" * 70)

sr_views = [
    "nasdaq_100_support_resistance",
    "nse_500_support_resistance",
    "Forex_support_resistance",
]

for view in sr_views:
    try:
        cursor.execute(f"SELECT TOP 1 * FROM [{view}]")
        cols = [desc[0] for desc in cursor.description]
        print(f"  OK  {view} — columns: {cols}")
    except Exception as e:
        print(f"  FAIL {view} — {e}")

# ============================================================
# PART 5: Test Pattern views
# ============================================================
print("\n" + "=" * 70)
print("PART 5: TESTING PATTERN VIEWS")
print("=" * 70)

pattern_views = [
    "nasdaq_100_patterns",
    "nse_500_patterns",
    "Forex_patterns",
]

for view in pattern_views:
    try:
        cursor.execute(f"SELECT TOP 1 * FROM [{view}]")
        cols = [desc[0] for desc in cursor.description]
        print(f"  OK  {view} — columns: {cols}")
    except Exception as e:
        print(f"  FAIL {view} — {e}")

# ============================================================
# PART 6: Test other SMA-referencing views
# ============================================================
print("\n" + "=" * 70)
print("PART 6: TESTING OTHER SMA-REFERENCING VIEWS")
print("=" * 70)

other_views = [
    "vw_PowerBI_Opportunities",
    "vw_strategy2_ml_tech_combined",
    "vw_market_calendar_features",
    "nse_500_stochastic",
]

for view in other_views:
    try:
        cursor.execute(f"SELECT TOP 1 * FROM [{view}]")
        cols = [desc[0] for desc in cursor.description]
        print(f"  OK  {view} — columns: {cols}")
    except Exception as e:
        print(f"  FAIL {view} — {e}")

# ============================================================
# PART 7: Test ALL agent queries end-to-end
# ============================================================
print("\n" + "=" * 70)
print("PART 7: TESTING ALL AGENT QUERIES")
print("=" * 70)

from config.sql_queries import (
    MARKET_INTEL_QUERIES,
    ML_ANALYST_QUERIES,
    TECH_SIGNAL_QUERIES,
    STRATEGY_TRADE_QUERIES,
    FOREX_QUERIES,
    RISK_QUERIES,
    CROSS_STRATEGY_QUERIES,
    VALUATION_QUERIES,
)

query_sets = [
    ("MARKET_INTEL", MARKET_INTEL_QUERIES),
    ("ML_ANALYST", ML_ANALYST_QUERIES),
    ("TECH_SIGNAL", TECH_SIGNAL_QUERIES),
    ("STRATEGY_TRADE", STRATEGY_TRADE_QUERIES),
    ("FOREX", FOREX_QUERIES),
    ("RISK", RISK_QUERIES),
    ("CROSS_STRATEGY", CROSS_STRATEGY_QUERIES),
    ("VALUATION", VALUATION_QUERIES),
]

total_pass = 0
total_fail = 0
failures = []

for set_name, queries in query_sets:
    print(f"\n  --- {set_name} ---")
    for qname, qsql in queries.items():
        try:
            start = time.time()
            cursor.execute(qsql)
            rows = cursor.fetchall()
            elapsed = time.time() - start
            print(f"    OK  {qname}: {len(rows)} rows ({elapsed:.1f}s)")
            total_pass += 1
        except Exception as e:
            err_msg = str(e)[:120]
            print(f"    FAIL {qname}: {err_msg}")
            failures.append((set_name, qname, err_msg))
            total_fail += 1

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print(f"SUMMARY: {total_pass} passed, {total_fail} failed")
print("=" * 70)

if failures:
    print("\nFAILED QUERIES:")
    for set_name, qname, err in failures:
        print(f"  [{set_name}] {qname}: {err}")
else:
    print("\nAll agent queries passed!")

cursor.close()
conn.close()
