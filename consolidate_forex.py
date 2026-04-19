"""Replace 9 Forex queries with 1 consolidated query."""

# Read the current file
with open('config/sql_queries.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# New consolidated Forex query
new_forex_queries = '''FOREX_QUERIES = {
    # ========================================================================
    # Consolidated Forex Analysis Query (All Data in 1 Query)
    # ========================================================================
    "forex_comprehensive_analysis": """
        WITH latest_rates AS (
            SELECT
                f.symbol,
                f.currency_from,
                f.currency_to,
                f.trading_date,
                f.open_price,
                f.high_price,
                f.low_price,
                f.close_price,
                f.daily_change,
                f.daily_change_pct,
                f.fifty_day_avg,
                f.two_hundred_day_avg
            FROM forex_hist_data f
            WHERE f.trading_date = (SELECT MAX(trading_date) FROM forex_hist_data)
        ),
        weekly_stats AS (
            SELECT
                symbol,
                MIN(close_price) AS week_low,
                MAX(close_price) AS week_high,
                (SELECT TOP 1 close_price FROM forex_hist_data f2
                 WHERE f2.symbol = f1.symbol
                 AND f1.trading_date >= DATEADD(DAY, -7, GETDATE())
                 ORDER BY f2.trading_date ASC) AS week_open,
                (SELECT TOP 1 close_price FROM forex_hist_data f3
                 WHERE f3.symbol = f1.symbol
                 AND f1.trading_date >= DATEADD(DAY, -7, GETDATE())
                 ORDER BY f3.trading_date DESC) AS week_close
            FROM forex_hist_data f1
            WHERE trading_date >= DATEADD(DAY, -7, GETDATE())
            GROUP BY symbol
        ),
        ml_signals AS (
            SELECT
                currency_pair,
                CAST(close_price AS FLOAT) AS ml_close_price,
                predicted_signal AS ml_signal,
                ROUND(CAST(signal_confidence AS FLOAT) * 100, 1) AS ml_confidence_pct,
                ROUND(CAST(prob_buy AS FLOAT), 3) AS prob_buy,
                ROUND(CAST(prob_sell AS FLOAT), 3) AS prob_sell,
                ROUND(CAST(prob_hold AS FLOAT), 3) AS prob_hold,
                model_name,
                model_version
            FROM forex_ml_predictions
            WHERE prediction_date = (SELECT MAX(prediction_date) FROM forex_ml_predictions)
        ),
        technical_indicators AS (
            SELECT
                r.symbol,
                r.trading_date,
                -- RSI
                ROUND(r.RSI, 1) AS rsi,
                CASE
                    WHEN r.RSI > 70 THEN 'OVERBOUGHT'
                    WHEN r.RSI < 30 THEN 'OVERSOLD'
                    WHEN r.RSI > 60 THEN 'BULLISH'
                    WHEN r.RSI < 40 THEN 'BEARISH'
                    ELSE 'NEUTRAL'
                END AS rsi_signal,
                -- MACD
                ROUND(m.MACD, 4) AS macd_line,
                ROUND(m.Signal_Line, 4) AS macd_signal_line,
                ROUND(m.MACD - m.Signal_Line, 4) AS macd_histogram,
                CASE
                    WHEN m.MACD > m.Signal_Line AND (m.MACD - m.Signal_Line) > 0 THEN 'BULLISH'
                    WHEN m.MACD < m.Signal_Line AND (m.MACD - m.Signal_Line) < 0 THEN 'BEARISH'
                    ELSE 'NEUTRAL'
                END AS macd_signal,
                -- Bollinger Bands
                ROUND(b.Upper_Band, 4) AS bb_upper,
                ROUND(b.Lower_Band, 4) AS bb_lower,
                ROUND(b.SMA_20, 4) AS bb_middle,
                CASE
                    WHEN b.close_price > b.Upper_Band THEN 'OVERBOUGHT'
                    WHEN b.close_price < b.Lower_Band THEN 'OVERSOLD'
                    ELSE 'IN-BAND'
                END AS bb_signal,
                -- Stochastic
                ROUND(s.stoch_14d_k, 1) AS stoch_k,
                ROUND(s.stoch_14d_d, 1) AS stoch_d,
                CASE
                    WHEN s.stoch_14d_k > 80 THEN 'OVERBOUGHT'
                    WHEN s.stoch_14d_k < 20 THEN 'OVERSOLD'
                    WHEN s.stoch_14d_k > s.stoch_14d_d THEN 'BULLISH'
                    WHEN s.stoch_14d_k < s.stoch_14d_d THEN 'BEARISH'
                    ELSE 'NEUTRAL'
                END AS stoch_signal,
                -- Technical Consensus Score
                (CASE WHEN r.RSI > 50 THEN 1 ELSE -1 END
                 + CASE WHEN m.MACD > m.Signal_Line THEN 1 ELSE -1 END
                 + CASE WHEN s.stoch_14d_k > s.stoch_14d_d THEN 1 ELSE -1 END
                 + CASE WHEN b.close_price > b.SMA_20 THEN 1 ELSE -1 END
                ) AS tech_score,
                CASE
                    WHEN (CASE WHEN r.RSI > 50 THEN 1 ELSE -1 END
                          + CASE WHEN m.MACD > m.Signal_Line THEN 1 ELSE -1 END
                          + CASE WHEN s.stoch_14d_k > s.stoch_14d_d THEN 1 ELSE -1 END
                          + CASE WHEN b.close_price > b.SMA_20 THEN 1 ELSE -1 END) >= 3
                    THEN 'STRONG BUY'
                    WHEN (CASE WHEN r.RSI > 50 THEN 1 ELSE -1 END
                          + CASE WHEN m.MACD > m.Signal_Line THEN 1 ELSE -1 END
                          + CASE WHEN s.stoch_14d_k > s.stoch_14d_d THEN 1 ELSE -1 END
                          + CASE WHEN b.close_price > b.SMA_20 THEN 1 ELSE -1 END) >= 1
                    THEN 'BUY'
                    WHEN (CASE WHEN r.RSI > 50 THEN 1 ELSE -1 END
                          + CASE WHEN m.MACD > m.Signal_Line THEN 1 ELSE -1 END
                          + CASE WHEN s.stoch_14d_k > s.stoch_14d_d THEN 1 ELSE -1 END
                          + CASE WHEN b.close_price > b.SMA_20 THEN 1 ELSE -1 END) <= -3
                    THEN 'STRONG SELL'
                    WHEN (CASE WHEN r.RSI > 50 THEN 1 ELSE -1 END
                          + CASE WHEN m.MACD > m.Signal_Line THEN 1 ELSE -1 END
                          + CASE WHEN s.stoch_14d_k > s.stoch_14d_d THEN 1 ELSE -1 END
                          + CASE WHEN b.close_price > b.SMA_20 THEN 1 ELSE -1 END) <= -1
                    THEN 'SELL'
                    ELSE 'HOLD'
                END AS tech_consensus
            FROM Forex_RSI_calculation r
            LEFT JOIN Forex_macd m ON r.symbol = m.symbol AND r.trading_date = m.trading_date
            LEFT JOIN Forex_bollingerband b ON r.symbol = b.symbol AND r.trading_date = b.trading_date
            LEFT JOIN Forex_stochastic s ON r.symbol = s.ticker AND s.trading_date = r.trading_date
            WHERE r.trading_date = (SELECT MAX(trading_date) FROM Forex_RSI_calculation)
        ),
        support_resistance AS (
            SELECT
                ticker AS symbol,
                s1 AS support_level,
                r1 AS resistance_level,
                s2 AS support_level_2,
                r2 AS resistance_level_2,
                pivot_point,
                ROUND(((r1 - close_price) / NULLIF(close_price, 0)) * 100, 2) AS pct_to_resistance,
                ROUND(((close_price - s1) / NULLIF(close_price, 0)) * 100, 2) AS pct_from_support,
                pivot_status,
                sr_trade_signal
            FROM Forex_support_resistance
            WHERE trading_date = (SELECT MAX(trading_date) FROM Forex_support_resistance)
        ),
        crossover_signals AS (
            SELECT
                ticker AS symbol,
                bb_trade_signal,
                macd_signal AS crossover_macd_signal,
                rsi_trade_signal,
                sma_trade_signal,
                stoch_signal AS crossover_stoch_signal,
                fib_signal,
                pattern_signal AS crossover_pattern_signal,
                bullish_count,
                bearish_count
            FROM vw_crossover_signals_Forex
            WHERE trading_date = (SELECT MAX(trading_date) FROM vw_crossover_signals_Forex)
        ),
        recent_patterns AS (
            SELECT
                ticker AS symbol,
                STRING_AGG(patterns_detected, '; ') AS recent_patterns,
                STRING_AGG(pattern_signal, ', ') AS pattern_signals
            FROM Forex_patterns
            WHERE trading_date >= DATEADD(DAY, -7, (SELECT MAX(trading_date) FROM Forex_patterns))
                AND pattern_signal IS NOT NULL
            GROUP BY ticker
        )
        -- Main SELECT combining all CTEs
        SELECT
            lr.symbol,
            lr.currency_from,
            lr.currency_to,
            lr.trading_date,
            lr.close_price,
            lr.open_price,
            lr.high_price,
            lr.low_price,
            lr.daily_change,
            lr.daily_change_pct,
            lr.fifty_day_avg,
            lr.two_hundred_day_avg,
            -- Weekly Stats
            ws.week_low,
            ws.week_high,
            ws.week_open,
            ws.week_close,
            -- ML Predictions
            ml.ml_signal,
            ml.ml_confidence_pct,
            ml.prob_buy,
            ml.prob_sell,
            ml.prob_hold,
            ml.model_name,
            -- Technical Indicators
            ti.rsi,
            ti.rsi_signal,
            ti.macd_line,
            ti.macd_signal_line,
            ti.macd_histogram,
            ti.macd_signal,
            ti.bb_upper,
            ti.bb_lower,
            ti.bb_middle,
            ti.bb_signal,
            ti.stoch_k,
            ti.stoch_d,
            ti.stoch_signal,
            ti.tech_score,
            ti.tech_consensus,
            -- Support/Resistance
            sr.support_level,
            sr.resistance_level,
            sr.support_level_2,
            sr.resistance_level_2,
            sr.pivot_point,
            sr.pct_to_resistance,
            sr.pct_from_support,
            sr.pivot_status,
            sr.sr_trade_signal,
            -- Crossover Signals
            cs.bb_trade_signal,
            cs.crossover_macd_signal,
            cs.rsi_trade_signal,
            cs.sma_trade_signal,
            cs.crossover_stoch_signal,
            cs.fib_signal,
            cs.crossover_pattern_signal,
            cs.bullish_count,
            cs.bearish_count,
            -- Recent Patterns
            rp.recent_patterns,
            rp.pattern_signals,
            -- Technical vs ML Agreement
            CASE
                WHEN (ti.tech_score >= 1 AND ml.ml_signal = 'Buy')
                  OR (ti.tech_score <= -1 AND ml.ml_signal = 'Sell')
                THEN 'ALIGNED'
                WHEN ml.ml_signal = 'Hold' THEN 'ML NEUTRAL'
                ELSE 'CONFLICTING'
            END AS tech_ml_agreement
        FROM latest_rates lr
        LEFT JOIN weekly_stats ws ON lr.symbol = ws.symbol
        LEFT JOIN ml_signals ml ON lr.symbol = ml.currency_pair
        LEFT JOIN technical_indicators ti ON lr.symbol = ti.symbol
        LEFT JOIN support_resistance sr ON lr.symbol = sr.symbol
        LEFT JOIN crossover_signals cs ON lr.symbol = cs.symbol
        LEFT JOIN recent_patterns rp ON lr.symbol = rp.symbol
        ORDER BY lr.symbol
    """,
}
'''

# FOREX_QUERIES is from line 545 to line 809 (indices 545-809)
forex_start = 545
forex_end = 810  # Include the closing brace

# Build new file content
new_content = ''.join(lines[:forex_start]) + new_forex_queries + '\n' + ''.join(lines[forex_end:])

# Write back
with open('config/sql_queries.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"✅ Replaced 9 Forex queries with 1 consolidated query")
print(f"  Old: Lines {forex_start+1}-{forex_end} ({forex_end - forex_start} lines)")
print(f"  New query: forex_comprehensive_analysis")
print(f"  Combines: rates + ML + technicals + support/resistance + crossovers + patterns")
