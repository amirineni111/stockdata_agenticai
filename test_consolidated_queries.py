"""Test the 2 consolidated cross-strategy queries."""
import pyodbc
from config.settings import get_sql_connection_string
from config.sql_queries import CROSS_STRATEGY_QUERIES


def test_consolidated_query(query_name: str, market: str):
    """Run a consolidated query and display results by category."""
    print(f"\n{'=' * 80}")
    print(f"{market} CROSS-STRATEGY - All Categories")
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
            
            # Group by category
            categories = {}
            for row in rows:
                cat = row[0]  # price_category
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(row)
            
            print(f"✅ {len(rows)} total stocks across {len(categories)} categories\n")
            
            # Display by category
            cat_names = {
                'Cat1_Below20': f'Category 1: Price < {market[0]}20',
                'Cat2_20to100': f'Category 2: Price {market[0]}20-{market[0]}100',
                'Cat3_100to200': f'Category 3: Price {market[0]}100-{market[0]}200',
                'Cat4_Above200': f'Category 4: Price > {market[0]}200'
            }
            
            for cat_key in ['Cat1_Below20', 'Cat2_20to100', 'Cat3_100to200', 'Cat4_Above200']:
                if cat_key in categories:
                    print(f"\n{cat_names[cat_key]}")
                    print("-" * 80)
                    for idx, row in enumerate(categories[cat_key][:5], 1):  # Show top 5 per category
                        ticker = row[1]
                        company = row[2]
                        s1_signal = row[3]
                        s1_conf = row[4]
                        s2_direction = row[6]
                        s2_change = row[7]
                        current_price = row[8]
                        target_price = row[9]
                        
                        print(f"  {idx}. {ticker:12} {company[:25]:25} | "
                              f"S1: {s1_signal:4} {s1_conf:5.1f}% | "
                              f"S2: {s2_direction:8} {s2_change:+6.2f}% | "
                              f"{market[0]}{current_price:.2f} → {market[0]}{target_price:.2f}")
                    print(f"     (Total {len(categories[cat_key])} stocks in this category)")
                else:
                    print(f"\n{cat_names[cat_key]}")
                    print("-" * 80)
                    print("  No stocks in this category")
    
    except Exception as e:
        print(f"❌ ERROR: {e}")


def main():
    """Test both consolidated queries."""
    print("\n" + "=" * 80)
    print("TESTING 2 CONSOLIDATED CROSS-STRATEGY QUERIES")
    print("=" * 80)
    
    test_consolidated_query("nse_all_categories", "₹")
    print("\n\n")
    test_consolidated_query("nasdaq_all_categories", "$")
    
    print("\n\n" + "=" * 80)
    print("TEST COMPLETE - Agent now runs 2 queries instead of 8!")
    print("This reduces API calls, speeds up execution, and saves Anthropic credits.")
    print("=" * 80)


if __name__ == "__main__":
    main()
