"""
Test the new 4-category cross-strategy queries for NSE and NASDAQ.
"""
import pyodbc
from config.settings import get_sql_connection_string
from config.sql_queries import CROSS_STRATEGY_QUERIES


def test_category_query(query_name: str, description: str):
    """Run a single category query and display results."""
    print(f"\n{'=' * 80}")
    print(f"{description}")
    print(f"Query: {query_name}")
    print(f"{'=' * 80}")
    
    conn_str = get_sql_connection_string()
    
    try:
        with pyodbc.connect(conn_str, timeout=30) as conn:
            cursor = conn.cursor()
            sql = CROSS_STRATEGY_QUERIES[query_name]
            cursor.execute(sql)
            
            rows = cursor.fetchall()
            if not rows:
                print(f"❌ NO RESULTS for {query_name}")
                return
            
            print(f"✅ {len(rows)} stocks found")
            print(f"\nTop results:")
            for idx, row in enumerate(rows[:5], 1):
                ticker = row[0]
                company = row[1]
                s1_signal = row[2]
                s1_conf = row[3]
                s2_direction = row[5]
                s2_change = row[6]
                current_price = row[7]
                target_price = row[8] if len(row) > 8 else None
                
                print(f"{idx}. {ticker:12} {company[:30]:30} | "
                      f"S1: {s1_signal:4} {s1_conf:5.1f}% | "
                      f"S2: {s2_direction:8} {s2_change:+6.2f}% | "
                      f"${current_price:.2f} → ${target_price:.2f}" if target_price 
                      else f"${current_price:.2f}")
    
    except Exception as e:
        print(f"❌ ERROR: {e}")


def main():
    """Test all 8 category queries."""
    print("\n" + "=" * 80)
    print("TESTING CROSS-STRATEGY 4-CATEGORY QUERIES")
    print("=" * 80)
    
    # NSE Categories
    print("\n\n🇮🇳 NSE 500 CATEGORIES")
    print("=" * 80)
    
    test_category_query(
        "nse_cat1_below_20",
        "Category 1: Price < ₹20"
    )
    
    test_category_query(
        "nse_cat2_20_to_100",
        "Category 2: Price ₹20-₹100"
    )
    
    test_category_query(
        "nse_cat3_100_to_200",
        "Category 3: Price ₹100-₹200"
    )
    
    test_category_query(
        "nse_cat4_above_200",
        "Category 4: Price > ₹200"
    )
    
    # NASDAQ Categories
    print("\n\n🇺🇸 NASDAQ 100 CATEGORIES")
    print("=" * 80)
    
    test_category_query(
        "nasdaq_cat1_below_20",
        "Category 1: Price < $20"
    )
    
    test_category_query(
        "nasdaq_cat2_20_to_100",
        "Category 2: Price $20-$100"
    )
    
    test_category_query(
        "nasdaq_cat3_100_to_200",
        "Category 3: Price $100-$200"
    )
    
    test_category_query(
        "nasdaq_cat4_above_200",
        "Category 4: Price > $200"
    )
    
    print("\n\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
