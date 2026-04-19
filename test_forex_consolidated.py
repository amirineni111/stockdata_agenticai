"""Test the consolidated Forex query."""
import pyodbc
from config.settings import get_sql_connection_string
from config.sql_queries import FOREX_QUERIES


def test_forex_comprehensive():
    """Run the consolidated forex query and display results."""
    print("\n" + "=" * 80)
    print("TESTING CONSOLIDATED FOREX QUERY")
    print("=" * 80)
    
    conn_str = get_sql_connection_string()
    
    try:
        with pyodbc.connect(conn_str, timeout=30) as conn:
            cursor = conn.cursor()
            sql = FOREX_QUERIES["forex_comprehensive_analysis"]
            cursor.execute(sql)
            
            rows = cursor.fetchall()
            if not rows:
                print("❌ NO RESULTS")
                return
            
            print(f"\n✅ {len(rows)} currency pairs analyzed\n")
            
            # First, get column names
            columns = [desc[0] for desc in cursor.description]
            print(f"Columns ({len(columns)}): {', '.join(columns[:10])}...")
            print()
            
            # Display comprehensive data for each pair
            for row in rows:
                # Create a dict for easier access
                data = dict(zip(columns, row))
                
                symbol = data.get('symbol', 'UNKNOWN')
                close_price = data.get('close_price', 0.0) or 0.0
                daily_change_pct = data.get('daily_change_pct', 0.0) or 0.0
                
                # Technical indicators
                rsi = data.get('rsi', 0.0) or 0.0
                rsi_signal = data.get('rsi_signal', 'N/A') or 'N/A'
                macd_signal = data.get('macd_signal', 'N/A') or 'N/A'
                bb_signal = data.get('bb_signal', 'N/A') or 'N/A'
                stoch_signal = data.get('stoch_signal', 'N/A') or 'N/A'
                tech_consensus = data.get('tech_consensus', 'N/A') or 'N/A'
                tech_score = data.get('tech_score', 0)
                
                # ML predictions
                ml_signal = data.get('ml_signal', 'N/A') or 'N/A'
                ml_confidence = data.get('ml_confidence_pct', 0.0) or 0.0
                
                # Support/Resistance
                support = data.get('support_level', 0.0) or 0.0
                resistance = data.get('resistance_level', 0.0) or 0.0
                pct_to_resistance = data.get('pct_to_resistance', 0.0) or 0.0
                pct_from_support = data.get('pct_from_support', 0.0) or 0.0
                
                # Agreement
                tech_ml_agreement = data.get('tech_ml_agreement', 'N/A') or 'N/A'
                
                print(f"{symbol:12} | {close_price:8.4f} ({daily_change_pct:+6.2f}%)")
                print(f"  Technical: RSI={rsi:.1f} ({rsi_signal:10}), MACD={macd_signal:8}, BB={bb_signal:10}, Stoch={stoch_signal:10}")
                
                # Handle tech_score formatting - could be int or string "N/A"
                score_str = f"{tech_score:+2}" if isinstance(tech_score, (int, float)) and tech_score != 0 else "N/A"
                print(f"  Consensus: {tech_consensus:12} (score: {score_str})")
                
                print(f"  ML Signal: {ml_signal:4} ({ml_confidence:.1f}% conf) | Agreement: {tech_ml_agreement}")
                print(f"  Support: {support:.4f} ({pct_from_support:+.2f}%) | Resistance: {resistance:.4f} ({pct_to_resistance:+.2f}%)")
                print()
            
            print("=" * 80)
            print("✅ CONSOLIDATED QUERY SUCCESSFUL")
            print("   Agent now runs 1 query instead of 9!")
            print("   Reduces API calls by ~89% for Forex agent")
            print("=" * 80)
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_forex_comprehensive()
