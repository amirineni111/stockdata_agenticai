"""
SQL query templates organized by agent domain.
Each agent has its own set of queries it can execute via the SQL tool.
"""

# =============================================================================
# Agent 1: Market Intelligence Agent Queries
# =============================================================================

MARKET_INTEL_QUERIES = {
    "nasdaq_top_movers": """
        SELECT TOP 5
            ticker,
            company,
            trading_date,
            CAST(close_price AS FLOAT) AS close_price,
            CAST(open_price AS FLOAT) AS open_price,
            CAST(volume AS BIGINT) AS volume,
            ROUND(
                ((CAST(close_price AS FLOAT) - CAST(open_price AS FLOAT))
                / NULLIF(CAST(open_price AS FLOAT), 0)) * 100, 2
            ) AS daily_change_pct
        FROM nasdaq_100_hist_data
        WHERE trading_date = (
            SELECT MAX(trading_date) FROM nasdaq_100_hist_data
        )
            AND CAST(close_price AS FLOAT) > 15
        ORDER BY ABS(
            (CAST(close_price AS FLOAT) - CAST(open_price AS FLOAT))
            / NULLIF(CAST(open_price AS FLOAT), 0)
        ) DESC
    """,

    "nse_top_movers": """
        SELECT TOP 5
            ticker,
            company,
            trading_date,
            CAST(close_price AS FLOAT) AS close_price,
            CAST(open_price AS FLOAT) AS open_price,
            CAST(volume AS BIGINT) AS volume,
            ROUND(
                ((CAST(close_price AS FLOAT) - CAST(open_price AS FLOAT))
                / NULLIF(CAST(open_price AS FLOAT), 0)) * 100, 2
            ) AS daily_change_pct
        FROM nse_500_hist_data
        WHERE trading_date = (
            SELECT MAX(trading_date) FROM nse_500_hist_data
        )
            AND CAST(close_price AS FLOAT) >= 20
        ORDER BY ABS(
            (CAST(close_price AS FLOAT) - CAST(open_price AS FLOAT))
            / NULLIF(CAST(open_price AS FLOAT), 0)
        ) DESC
    """,

    "nasdaq_market_summary": """
        SELECT
            COUNT(*) AS total_stocks,
            SUM(CASE WHEN CAST(close_price AS FLOAT) > CAST(open_price AS FLOAT)
                THEN 1 ELSE 0 END) AS stocks_up,
            SUM(CASE WHEN CAST(close_price AS FLOAT) < CAST(open_price AS FLOAT)
                THEN 1 ELSE 0 END) AS stocks_down,
            SUM(CASE WHEN CAST(close_price AS FLOAT) = CAST(open_price AS FLOAT)
                THEN 1 ELSE 0 END) AS stocks_flat,
            ROUND(AVG(
                ((CAST(close_price AS FLOAT) - CAST(open_price AS FLOAT))
                / NULLIF(CAST(open_price AS FLOAT), 0)) * 100
            ), 2) AS avg_change_pct,
            MAX(trading_date) AS latest_date
        FROM nasdaq_100_hist_data
        WHERE trading_date = (
            SELECT MAX(trading_date) FROM nasdaq_100_hist_data
        )
    """,

    "nse_market_summary": """
        SELECT
            COUNT(*) AS total_stocks,
            SUM(CASE WHEN CAST(close_price AS FLOAT) > CAST(open_price AS FLOAT)
                THEN 1 ELSE 0 END) AS stocks_up,
            SUM(CASE WHEN CAST(close_price AS FLOAT) < CAST(open_price AS FLOAT)
                THEN 1 ELSE 0 END) AS stocks_down,
            SUM(CASE WHEN CAST(close_price AS FLOAT) = CAST(open_price AS FLOAT)
                THEN 1 ELSE 0 END) AS stocks_flat,
            ROUND(AVG(
                ((CAST(close_price AS FLOAT) - CAST(open_price AS FLOAT))
                / NULLIF(CAST(open_price AS FLOAT), 0)) * 100
            ), 2) AS avg_change_pct,
            MAX(trading_date) AS latest_date
        FROM nse_500_hist_data
        WHERE trading_date = (
            SELECT MAX(trading_date) FROM nse_500_hist_data
        )
    """,
}

# =============================================================================
# Agent 2: ML Model Analyst Agent Queries
# =============================================================================

ML_ANALYST_QUERIES = {
    "model_accuracy_last_7_days": """
        SELECT
            model_name,
            COUNT(*) AS total_predictions,
            SUM(CASE WHEN direction_correct = 1 THEN 1 ELSE 0 END) AS correct_predictions,
            ROUND(
                CAST(SUM(CASE WHEN direction_correct = 1 THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(COUNT(*), 0) * 100, 2
            ) AS accuracy_pct,
            ROUND(AVG(CAST(absolute_error AS FLOAT)), 4) AS avg_absolute_error,
            ROUND(AVG(CAST(percentage_error AS FLOAT)), 2) AS avg_pct_error
        FROM ai_prediction_history
        WHERE target_date >= DATEADD(DAY, -7, GETDATE())
            AND actual_price IS NOT NULL
        GROUP BY model_name
        ORDER BY accuracy_pct DESC
    """,

    "model_accuracy_last_30_days": """
        SELECT
            model_name,
            COUNT(*) AS total_predictions,
            SUM(CASE WHEN direction_correct = 1 THEN 1 ELSE 0 END) AS correct_predictions,
            ROUND(
                CAST(SUM(CASE WHEN direction_correct = 1 THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(COUNT(*), 0) * 100, 2
            ) AS accuracy_pct,
            ROUND(AVG(CAST(absolute_error AS FLOAT)), 4) AS avg_absolute_error,
            ROUND(AVG(CAST(percentage_error AS FLOAT)), 2) AS avg_pct_error
        FROM ai_prediction_history
        WHERE target_date >= DATEADD(DAY, -30, GETDATE())
            AND actual_price IS NOT NULL
        GROUP BY model_name
        ORDER BY accuracy_pct DESC
    """,

    "model_accuracy_by_market": """
        SELECT
            market,
            model_name,
            COUNT(*) AS total_predictions,
            ROUND(
                CAST(SUM(CASE WHEN direction_correct = 1 THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(COUNT(*), 0) * 100, 2
            ) AS accuracy_pct,
            ROUND(AVG(CAST(absolute_error AS FLOAT)), 4) AS avg_absolute_error
        FROM ai_prediction_history
        WHERE target_date >= DATEADD(DAY, -7, GETDATE())
            AND actual_price IS NOT NULL
        GROUP BY market, model_name
        ORDER BY market, accuracy_pct DESC
    """,

    "recent_predictions_summary": """
        SELECT TOP 5
            ticker,
            company_name,
            market,
            model_name,
            prediction_date,
            target_date,
            current_price,
            predicted_price,
            predicted_change_pct,
            actual_price,
            actual_change_pct,
            direction_correct,
            model_confidence
        FROM ai_prediction_history
        WHERE prediction_date = (
            SELECT MAX(prediction_date) FROM ai_prediction_history
        )
            AND ((market = 'NASDAQ 100' AND CAST(current_price AS FLOAT) > 15)
                 OR (market = 'NSE 500' AND CAST(current_price AS FLOAT) >= 20))
        ORDER BY model_confidence DESC
    """,

    # --- Strategy 1: ML Classifier Model Health (ml_trading_predictions) ---

    "strategy1_nasdaq_ml_summary": """
        SELECT TOP 1
            s.run_date AS latest_date,
            s.total_predictions,
            s.buy_signals,
            s.sell_signals,
            s.high_confidence_count,
            ROUND(s.avg_confidence, 1) AS avg_confidence,
            s.bullish_macd_count,
            s.bearish_macd_count,
            s.uptrend_count,
            s.downtrend_count,
            s.sideways_count
        FROM ml_prediction_summary s
        ORDER BY s.run_date DESC
    """,

    "strategy1_nse_ml_summary": """
        SELECT TOP 1
            s.analysis_date AS latest_date,
            s.total_predictions,
            s.total_buy_signals AS buy_signals,
            s.total_sell_signals AS sell_signals,
            s.high_confidence_count,
            s.medium_confidence_count,
            s.low_confidence_count,
            ROUND(s.avg_confidence, 3) AS avg_confidence,
            s.market_trend,
            s.model_accuracy,
            s.success_rate_1d,
            s.success_rate_5d,
            s.success_rate_10d,
            s.total_stocks_processed
        FROM ml_nse_predict_summary s
        ORDER BY s.analysis_date DESC
    """,

    # --- Strategy 1: Forex ML Classifier Health (forex_ml_predictions) ---

    "strategy1_forex_ml_summary": """
        SELECT
            predicted_signal,
            COUNT(*) AS total_predictions,
            ROUND(CAST(AVG(signal_confidence) AS FLOAT) * 100, 1) AS avg_confidence_pct,
            ROUND(CAST(AVG(prob_buy) AS FLOAT), 3) AS avg_prob_buy,
            ROUND(CAST(AVG(prob_sell) AS FLOAT), 3) AS avg_prob_sell,
            ROUND(CAST(AVG(prob_hold) AS FLOAT), 3) AS avg_prob_hold,
            MAX(prediction_date) AS latest_date
        FROM forex_ml_predictions
        WHERE prediction_date = (SELECT MAX(prediction_date) FROM forex_ml_predictions)
        GROUP BY predicted_signal
    """,

    "strategy1_forex_ml_accuracy": """
        SELECT
            predicted_signal,
            COUNT(*) AS total,
            SUM(CASE WHEN direction_correct_1d = 1 THEN 1 ELSE 0 END) AS correct_1d,
            ROUND(
                CAST(SUM(CASE WHEN direction_correct_1d = 1 THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(COUNT(CASE WHEN direction_correct_1d IS NOT NULL THEN 1 END), 0) * 100, 1
            ) AS accuracy_1d_pct,
            ROUND(CAST(AVG(signal_confidence) AS FLOAT) * 100, 1) AS avg_confidence_pct
        FROM forex_ml_predictions
        WHERE prediction_date >= DATEADD(DAY, -7, (SELECT MAX(prediction_date) FROM forex_ml_predictions))
            AND direction_correct_1d IS NOT NULL
        GROUP BY predicted_signal
    """,
}

# =============================================================================
# Agent 3: Technical Signal Agent Queries
# =============================================================================

TECH_SIGNAL_QUERIES = {
    "active_signals_today": """
        SELECT TOP 15
            v.market,
            v.ticker,
            v.company_name,
            v.signal_date,
            v.signal_type,
            v.signal_strength,
            v.trade_tier,
            v.signal_price,
            v.ai_prediction_pct,
            v.technical_combo,
            v.macd_signal,
            v.rsi_signal,
            v.bb_signal,
            v.stoch_signal,
            v.fib_signal,
            v.pattern_signal
        FROM vw_PowerBI_AI_Technical_Combos v
        INNER JOIN (
            SELECT market, MAX(signal_date) AS max_date
            FROM vw_PowerBI_AI_Technical_Combos
            GROUP BY market
        ) latest ON v.market = latest.market AND v.signal_date = latest.max_date
        WHERE ((v.market = 'NASDAQ 100' AND v.signal_price > 15)
               OR (v.market = 'NSE 500' AND v.signal_price >= 20))
        ORDER BY v.signal_strength DESC
    """,

    "signal_outcomes_7d": """
        SELECT
            signal_type,
            COUNT(*) AS total_signals,
            SUM(CASE WHEN result_7d = 'CORRECT' THEN 1 ELSE 0 END) AS correct_7d,
            ROUND(
                CAST(SUM(CASE WHEN result_7d = 'CORRECT' THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(COUNT(*), 0) * 100, 2
            ) AS accuracy_7d_pct,
            ROUND(AVG(CAST(actual_change_7d AS FLOAT)), 2) AS avg_change_7d
        FROM signal_tracking_history
        WHERE result_7d IS NOT NULL
            AND signal_date >= DATEADD(DAY, -30, GETDATE())
        GROUP BY signal_type
    """,

    "signal_outcomes_14d": """
        SELECT
            signal_type,
            COUNT(*) AS total_signals,
            SUM(CASE WHEN result_14d = 'CORRECT' THEN 1 ELSE 0 END) AS correct_14d,
            ROUND(
                CAST(SUM(CASE WHEN result_14d = 'CORRECT' THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(COUNT(*), 0) * 100, 2
            ) AS accuracy_14d_pct,
            ROUND(AVG(CAST(actual_change_14d AS FLOAT)), 2) AS avg_change_14d
        FROM signal_tracking_history
        WHERE result_14d IS NOT NULL
            AND signal_date >= DATEADD(DAY, -30, GETDATE())
        GROUP BY signal_type
    """,

    "strongest_signals_recent": """
        SELECT TOP 15
            v.market,
            v.ticker,
            v.company_name,
            v.signal_date,
            v.signal_type,
            v.signal_strength,
            v.trade_tier,
            v.signal_price,
            v.ai_prediction_pct,
            v.technical_combo,
            v.macd_signal,
            v.rsi_signal,
            v.stoch_signal,
            v.fib_signal,
            v.pattern_signal
        FROM vw_PowerBI_AI_Technical_Combos v
        INNER JOIN (
            SELECT market, MAX(signal_date) AS max_date
            FROM vw_PowerBI_AI_Technical_Combos
            GROUP BY market
        ) latest ON v.market = latest.market AND v.signal_date = latest.max_date
        WHERE v.signal_strength >= 2
            AND ((v.market = 'NASDAQ 100' AND v.signal_price > 15)
                 OR (v.market = 'NSE 500' AND v.signal_price >= 20))
        ORDER BY v.signal_strength DESC, v.market
    """,
}

# =============================================================================
# Agent 4: Strategy & Trade Agent Queries
# (Uses vw_PowerBI_AI_Technical_Combos -- the live view with TIER classifications)
# =============================================================================

STRATEGY_TRADE_QUERIES = {
    "top_tier1_opportunities": """
        SELECT TOP 15
            v.market,
            v.ticker,
            v.company_name,
            v.signal_date,
            v.signal_type,
            v.signal_strength,
            v.trade_tier,
            v.ai_prediction_pct,
            v.technical_combo,
            v.signal_price,
            v.macd_signal,
            v.rsi_signal,
            v.bb_signal,
            v.stoch_signal,
            v.fib_signal,
            v.pattern_signal
        FROM vw_PowerBI_AI_Technical_Combos v
        INNER JOIN (
            SELECT market, MAX(signal_date) AS max_date
            FROM vw_PowerBI_AI_Technical_Combos
            GROUP BY market
        ) latest ON v.market = latest.market AND v.signal_date = latest.max_date
        WHERE v.trade_tier LIKE 'TIER 1%'
            AND ((v.market = 'NASDAQ 100' AND v.signal_price > 15)
                 OR (v.market = 'NSE 500' AND v.signal_price >= 20))
        ORDER BY v.signal_strength DESC, ABS(v.ai_prediction_pct) DESC
    """,

    "top_tier2_opportunities": """
        SELECT TOP 15
            v.market,
            v.ticker,
            v.company_name,
            v.signal_date,
            v.signal_type,
            v.signal_strength,
            v.trade_tier,
            v.ai_prediction_pct,
            v.technical_combo,
            v.signal_price,
            v.macd_signal,
            v.rsi_signal,
            v.stoch_signal,
            v.fib_signal,
            v.pattern_signal
        FROM vw_PowerBI_AI_Technical_Combos v
        INNER JOIN (
            SELECT market, MAX(signal_date) AS max_date
            FROM vw_PowerBI_AI_Technical_Combos
            GROUP BY market
        ) latest ON v.market = latest.market AND v.signal_date = latest.max_date
        WHERE v.trade_tier LIKE 'TIER 2%'
            AND ((v.market = 'NASDAQ 100' AND v.signal_price > 15)
                 OR (v.market = 'NSE 500' AND v.signal_price >= 20))
        ORDER BY v.signal_strength DESC, ABS(v.ai_prediction_pct) DESC
    """,

    "tier_summary_today": """
        SELECT
            v.market,
            v.trade_tier,
            COUNT(*) AS total_signals,
            SUM(CASE WHEN v.signal_type = 'BULLISH' THEN 1 ELSE 0 END) AS bullish_count,
            SUM(CASE WHEN v.signal_type = 'BEARISH' THEN 1 ELSE 0 END) AS bearish_count,
            ROUND(AVG(CAST(v.ai_prediction_pct AS FLOAT)), 2) AS avg_ai_prediction_pct,
            AVG(v.signal_strength) AS avg_signal_strength
        FROM vw_PowerBI_AI_Technical_Combos v
        INNER JOIN (
            SELECT market, MAX(signal_date) AS max_date
            FROM vw_PowerBI_AI_Technical_Combos
            GROUP BY market
        ) latest ON v.market = latest.market AND v.signal_date = latest.max_date
        GROUP BY v.market, v.trade_tier
        ORDER BY v.market, v.trade_tier
    """,

    "open_trades": """
        SELECT
            ticker,
            company_name,
            signal_type,
            entry_date,
            entry_price,
            target_price,
            stop_loss_price,
            predicted_change_pct,
            model_confidence,
            trade_status,
            notes
        FROM trade_log
        WHERE trade_status = 'OPEN'
        ORDER BY entry_date DESC
    """,

    "nasdaq_tier1_today": """
        SELECT TOP 10
            ticker,
            company_name,
            signal_type,
            trade_tier,
            ai_prediction_pct,
            technical_combo,
            signal_price,
            signal_strength
        FROM vw_PowerBI_AI_Technical_Combos
        WHERE trade_tier LIKE 'TIER 1%'
            AND market = 'NASDAQ 100'
            AND signal_price > 15
            AND signal_date = (
                SELECT MAX(signal_date) FROM vw_PowerBI_AI_Technical_Combos
                WHERE market = 'NASDAQ 100'
            )
        ORDER BY signal_strength DESC, ABS(ai_prediction_pct) DESC
    """,

    "nse_tier1_today": """
        SELECT TOP 10
            ticker,
            company_name,
            signal_type,
            trade_tier,
            ai_prediction_pct,
            technical_combo,
            signal_price,
            signal_strength
        FROM vw_PowerBI_AI_Technical_Combos
        WHERE trade_tier LIKE 'TIER 1%'
            AND market = 'NSE 500'
            AND signal_price >= 20
            AND signal_date = (
                SELECT MAX(signal_date) FROM vw_PowerBI_AI_Technical_Combos
                WHERE market = 'NSE 500'
            )
        ORDER BY signal_strength DESC, ABS(ai_prediction_pct) DESC
    """,

    # --- Strategy 1 ML Classifier: Top Buy/Sell Signals ---

    "strategy1_nasdaq_top_signals": """
        SELECT TOP 10
            ticker,
            company,
            trading_date,
            predicted_signal,
            ROUND(confidence_percentage, 1) AS confidence_pct,
            signal_strength,
            ROUND(RSI, 1) AS rsi,
            rsi_category,
            ROUND(buy_probability, 3) AS buy_prob,
            ROUND(sell_probability, 3) AS sell_prob,
            ROUND(CAST(close_price AS FLOAT), 2) AS close_price
        FROM ml_trading_predictions
        WHERE trading_date = (SELECT MAX(trading_date) FROM ml_trading_predictions)
            AND signal_strength IN ('Strong', 'Moderate')
            AND confidence_percentage >= 60
            AND CAST(close_price AS FLOAT) > 15
        ORDER BY confidence_percentage DESC
    """,

    "strategy1_nse_top_signals": """
        SELECT TOP 10
            t.ticker,
            t.company,
            t.trading_date,
            t.predicted_signal,
            ROUND(t.confidence_percentage, 1) AS confidence_pct,
            t.signal_strength,
            ROUND(t.rsi, 1) AS rsi,
            t.rsi_category,
            ROUND(t.buy_probability, 3) AS buy_prob,
            ROUND(t.sell_probability, 3) AS sell_prob,
            ROUND(CAST(t.close_price AS FLOAT), 2) AS close_price,
            t.model_name,
            t.sector
        FROM ml_nse_trading_predictions t
        INNER JOIN (
            SELECT MAX(trading_date) AS max_date FROM ml_nse_trading_predictions
        ) latest ON t.trading_date = latest.max_date
        WHERE t.signal_strength IN ('High', 'Medium')
            AND t.high_confidence = 1
            AND t.confidence_percentage >= 60
            AND CAST(t.close_price AS FLOAT) >= 20
        ORDER BY t.confidence_percentage DESC
    """,
}

# =============================================================================
# Agent 5: Forex Analysis Agent Queries
# =============================================================================

FOREX_QUERIES = {
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
                 AND f2.trading_date >= DATEADD(DAY, -7, GETDATE())
                 ORDER BY f2.trading_date ASC) AS week_open,
                (SELECT TOP 1 close_price FROM forex_hist_data f3
                 WHERE f3.symbol = f1.symbol
                 AND f3.trading_date >= DATEADD(DAY, -7, GETDATE())
                 ORDER BY f3.trading_date DESC) AS week_close
            FROM forex_hist_data f1
            WHERE f1.trading_date >= DATEADD(DAY, -7, GETDATE())
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


# =============================================================================
# Agent 6: Risk Assessment Agent Queries
# =============================================================================

RISK_QUERIES = {
    "portfolio_positions": """
        SELECT
            ticker,
            market,
            buy_date,
            buy_price,
            buy_qty,
            sell_date,
            sell_price,
            sell_qty,
            status,
            notes
        FROM portfolio_tracker
        WHERE status = 'OPEN' OR status IS NULL
        ORDER BY buy_date DESC
    """,

    "active_alerts": """
        SELECT
            ticker,
            alert_type,
            min_confidence,
            min_historical_accuracy,
            min_predicted_change,
            is_active,
            notify_email
        FROM trading_alerts
        WHERE is_active = 1
    """,

    "high_risk_positions": """
        SELECT TOP 15
            s2.market,
            s2.ticker,
            s2.company,
            s2.ml_signal,
            s2.ml_direction,
            ROUND(s2.ml_confidence_pct, 1) AS ml_confidence_pct,
            s2.trade_grade,
            s2.rsi_category,
            s2.rsi_assessment,
            s2.recommended_action,
            s2.tech_signal,
            s2.tech_signal_strength,
            CASE
                WHEN s2.signals_aligned = 0 THEN 'CONFLICTING'
                ELSE 'ALIGNED'
            END AS signal_alignment,
            s2.opportunity_score
        FROM vw_strategy2_trade_opportunities s2
        INNER JOIN (
            SELECT market, MAX(prediction_date) AS max_date
            FROM vw_strategy2_trade_opportunities
            GROUP BY market
        ) latest ON s2.market = latest.market AND s2.prediction_date = latest.max_date
        WHERE s2.signals_aligned = 0
        ORDER BY s2.ml_confidence_pct DESC
    """,

    "conflicting_signals": """
        SELECT TOP 15
            v.market,
            v.ticker,
            v.company_name,
            v.signal_type AS tech_direction,
            v.ai_prediction_pct,
            v.trade_tier,
            v.technical_combo,
            s2.ml_signal AS ml_direction,
            ROUND(s2.ml_confidence_pct, 1) AS ml_confidence_pct,
            s2.trade_grade,
            CASE
                WHEN (v.signal_type = 'BEARISH' AND s2.ml_signal IN ('Sell','SELL'))
                  OR (v.signal_type = 'BULLISH' AND s2.ml_signal IN ('Buy','BUY'))
                THEN 'ALIGNED'
                ELSE 'CONFLICTING'
            END AS cross_strategy_status
        FROM vw_PowerBI_AI_Technical_Combos v
        INNER JOIN (
            SELECT market, MAX(signal_date) AS max_date
            FROM vw_PowerBI_AI_Technical_Combos
            GROUP BY market
        ) latest ON v.market = latest.market AND v.signal_date = latest.max_date
        INNER JOIN vw_strategy2_trade_opportunities s2
            ON v.ticker = s2.ticker
        INNER JOIN (
            SELECT market, MAX(prediction_date) AS max_date
            FROM vw_strategy2_trade_opportunities
            GROUP BY market
        ) s2_latest ON s2.market = s2_latest.market AND s2.prediction_date = s2_latest.max_date
        WHERE (
            (v.signal_type = 'BEARISH' AND s2.ml_signal IN ('Buy','BUY'))
            OR (v.signal_type = 'BULLISH' AND s2.ml_signal IN ('Sell','SELL'))
        )
        ORDER BY s2.ml_confidence_pct DESC
    """,

    "family_assets_summary": """
        SELECT
            asset_type,
            COUNT(*) AS total_items,
            SUM(CASE WHEN current_status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_items,
            SUM(CASE WHEN current_status = 'ACTIVE' THEN purchase_value ELSE 0 END) AS total_active_value
        FROM family_assets
        GROUP BY asset_type
    """,
}

# =============================================================================
# Cross-Strategy Analysis Queries
# (Finds common recommendations between Strategy 1 and Strategy 2)
# =============================================================================

CROSS_STRATEGY_QUERIES = {
    # ========================================================================
    # NSE 500 Cross-Strategy (All 4 Price Categories in 1 Query)
    # ========================================================================
    "nse_all_categories": """
        WITH s1_ml AS (
            SELECT
                ml.ticker,
                nse.company_name,
                ml.predicted_signal,
                ROUND(ml.confidence_percentage, 1) AS ml_confidence_pct,
                ml.signal_strength,
                CAST(ml.close_price AS FLOAT) AS current_price,
                CASE
                    WHEN CAST(ml.close_price AS FLOAT) < 20 THEN 'Cat1_Below20'
                    WHEN CAST(ml.close_price AS FLOAT) < 100 THEN 'Cat2_20to100'
                    WHEN CAST(ml.close_price AS FLOAT) < 200 THEN 'Cat3_100to200'
                    ELSE 'Cat4_Above200'
                END AS price_category
            FROM ml_nse_trading_predictions ml
            INNER JOIN nse_500 nse ON ml.ticker = nse.ticker
            INNER JOIN (
                SELECT MAX(trading_date) AS max_date FROM ml_nse_trading_predictions
            ) latest ON ml.trading_date = latest.max_date
            WHERE ml.signal_strength IN ('High', 'Medium')
              AND ml.confidence_percentage >= 55
        ),
        s2_ai AS (
            SELECT
                ai.ticker,
                ai.predicted_price,
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
            INNER JOIN nse_500_hist_data hist 
                ON ai.ticker = hist.ticker 
                AND ai.prediction_date = hist.trading_date
            INNER JOIN (
                SELECT MAX(prediction_date) AS max_date 
                FROM ai_prediction_history 
                WHERE days_ahead = 3
            ) latest ON ai.prediction_date = latest.max_date
            WHERE ai.days_ahead = 3
              AND ai.model_name = 'Ensemble'
        ),
        aligned AS (
            SELECT
                s1.ticker,
                s1.company_name,
                s1.predicted_signal AS s1_ml_signal,
                s1.ml_confidence_pct,
                s1.signal_strength,
                s2.ai_direction AS s2_ai_direction,
                s2.ai_change_pct AS s2_predicted_change_pct,
                s1.current_price,
                s2.predicted_price AS s2_target_price,
                s1.price_category,
                ROW_NUMBER() OVER (PARTITION BY s1.price_category ORDER BY s1.ml_confidence_pct DESC) AS rn
            FROM s1_ml s1
            INNER JOIN s2_ai s2 ON s1.ticker = s2.ticker
            WHERE (
                (s1.predicted_signal IN ('Buy', 'BUY') AND s2.ai_direction = 'BULLISH')
                OR (s1.predicted_signal IN ('Sell', 'SELL') AND s2.ai_direction = 'BEARISH')
            )
        )
        SELECT
            price_category,
            ticker,
            company_name,
            s1_ml_signal,
            ml_confidence_pct,
            signal_strength,
            s2_ai_direction,
            s2_predicted_change_pct,
            current_price,
            s2_target_price
        FROM aligned
        WHERE rn <= 10
        ORDER BY 
            CASE price_category
                WHEN 'Cat1_Below20' THEN 1
                WHEN 'Cat2_20to100' THEN 2
                WHEN 'Cat3_100to200' THEN 3
                WHEN 'Cat4_Above200' THEN 4
            END,
            ml_confidence_pct DESC
    """,
    
    # ========================================================================
    # NASDAQ 100 Cross-Strategy (All 4 Price Categories in 1 Query)
    # ========================================================================
    "nasdaq_all_categories": """
        WITH s1_ml AS (
            SELECT
                ml.ticker,
                nasdaq.company_name,
                ml.predicted_signal,
                ROUND(ml.confidence_percentage, 1) AS ml_confidence_pct,
                ml.signal_strength,
                CAST(ml.close_price AS FLOAT) AS current_price,
                CASE
                    WHEN CAST(ml.close_price AS FLOAT) < 20 THEN 'Cat1_Below20'
                    WHEN CAST(ml.close_price AS FLOAT) < 100 THEN 'Cat2_20to100'
                    WHEN CAST(ml.close_price AS FLOAT) < 200 THEN 'Cat3_100to200'
                    ELSE 'Cat4_Above200'
                END AS price_category
            FROM ml_trading_predictions ml
            INNER JOIN nasdaq_top100 nasdaq ON ml.ticker = nasdaq.ticker
            INNER JOIN (
                SELECT MAX(trading_date) AS max_date FROM ml_trading_predictions
            ) latest ON ml.trading_date = latest.max_date
            WHERE ml.signal_strength IN ('Strong', 'Moderate')
              AND ml.confidence_percentage >= 55
        ),
        s2_ai AS (
            SELECT
                ai.ticker,
                ai.predicted_price,
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
        ),
        aligned AS (
            SELECT
                s1.ticker,
                s1.company_name,
                s1.predicted_signal AS s1_ml_signal,
                s1.ml_confidence_pct,
                s1.signal_strength,
                s2.ai_direction AS s2_ai_direction,
                s2.ai_change_pct AS s2_predicted_change_pct,
                s1.current_price,
                s2.predicted_price AS s2_target_price,
                s1.price_category,
                ROW_NUMBER() OVER (PARTITION BY s1.price_category ORDER BY s1.ml_confidence_pct DESC) AS rn
            FROM s1_ml s1
            INNER JOIN s2_ai s2 ON s1.ticker = s2.ticker
            WHERE (
                (s1.predicted_signal IN ('Buy', 'BUY') AND s2.ai_direction = 'BULLISH')
                OR (s1.predicted_signal IN ('Sell', 'SELL') AND s2.ai_direction = 'BEARISH')
            )
        )
        SELECT
            price_category,
            ticker,
            company_name,
            s1_ml_signal,
            ml_confidence_pct,
            signal_strength,
            s2_ai_direction,
            s2_predicted_change_pct,
            current_price,
            s2_target_price
        FROM aligned
        WHERE rn <= 10
        ORDER BY 
            CASE price_category
                WHEN 'Cat1_Below20' THEN 1
                WHEN 'Cat2_20to100' THEN 2
                WHEN 'Cat3_100to200' THEN 3
                WHEN 'Cat4_Above200' THEN 4
            END,
            ml_confidence_pct DESC
    """,
}

# =============================================================================
# Agent 8: Fair Value / Valuation Agent Queries (NOT CURRENTLY IN USE)
# (Uses vw_fair_value_estimates view for Graham Number, PEG, Forward Earnings, EPV)
# =============================================================================

# NOTE: Valuation agent is not included in the daily briefing pipeline.
# These queries are preserved for future use but currently inactive.

VALUATION_QUERIES = {
    # "nasdaq_top20_undervalued": """
    #     SELECT TOP 20
    #         ticker,
    #         company_name,
    #         market,
    #         sector,
    #         industry,
    #         implied_current_price,
    #         graham_number,
    #         peg_fair_value,
    #         forward_earnings_value,
    #         earnings_power_value,
    #         composite_fair_value,
    #         margin_of_safety_pct,
    #         valuation_verdict,
    #         trailing_pe,
    #         forward_pe,
    #         price_to_book,
    #         earnings_growth,
    #         return_on_equity,
    #         beta
    #     FROM vw_fair_value_estimates
    #     WHERE market = 'NASDAQ'
    #       AND composite_fair_value IS NOT NULL
    #       AND implied_current_price IS NOT NULL
    #       AND implied_current_price > 15
    #       AND valuation_verdict IN ('SIGNIFICANTLY UNDERVALUED', 'UNDERVALUED', 'FAIRLY VALUED')
    #     ORDER BY margin_of_safety_pct DESC
    # """,

    # "nse_top20_undervalued": """
    #     SELECT TOP 20
    #         ticker,
    #         company_name,
    #         market,
    #         sector,
    #         industry,
    #         implied_current_price,
    #         graham_number,
    #         peg_fair_value,
    #         forward_earnings_value,
    #         earnings_power_value,
    #         composite_fair_value,
    #         margin_of_safety_pct,
    #         valuation_verdict,
    #         trailing_pe,
    #         forward_pe,
    #         price_to_book,
    #         earnings_growth,
    #         return_on_equity,
    #         beta
    #     FROM vw_fair_value_estimates
    #     WHERE market = 'NSE'
    #       AND composite_fair_value IS NOT NULL
    #       AND implied_current_price IS NOT NULL
    #       AND implied_current_price >= 20
    #       AND valuation_verdict IN ('SIGNIFICANTLY UNDERVALUED', 'UNDERVALUED', 'FAIRLY VALUED')
    #     ORDER BY margin_of_safety_pct DESC
    # """,

    # "valuation_summary_by_market": """
    #     SELECT
    #         market,
    #         valuation_verdict,
    #         COUNT(*) AS stock_count,
    #         ROUND(AVG(margin_of_safety_pct), 2) AS avg_margin_of_safety,
    #         ROUND(AVG(trailing_pe), 2) AS avg_pe,
    #         ROUND(AVG(return_on_equity), 4) AS avg_roe
    #     FROM vw_fair_value_estimates
    #     WHERE composite_fair_value IS NOT NULL
    #       AND implied_current_price IS NOT NULL
    #     GROUP BY market, valuation_verdict
    #     ORDER BY market, 
    #         CASE valuation_verdict
    #             WHEN 'SIGNIFICANTLY UNDERVALUED' THEN 1
    #             WHEN 'UNDERVALUED' THEN 2
    #             WHEN 'FAIRLY VALUED' THEN 3
    #             WHEN 'OVERVALUED' THEN 4
    #             ELSE 5
    #         END
    # """,

    # "nasdaq_top20_overvalued": """
    #     SELECT TOP 20
    #         ticker,
    #         company_name,
    #         market,
    #         sector,
    #         industry,
    #         implied_current_price,
    #         graham_number,
    #         peg_fair_value,
    #         forward_earnings_value,
    #         earnings_power_value,
    #         composite_fair_value,
    #         margin_of_safety_pct,
    #         valuation_verdict,
    #         trailing_pe,
    #         forward_pe,
    #         price_to_book,
    #         earnings_growth,
    #         return_on_equity,
    #         beta
    #     FROM vw_fair_value_estimates
    #     WHERE market = 'NASDAQ'
    #       AND composite_fair_value IS NOT NULL
    #       AND implied_current_price IS NOT NULL
    #       AND valuation_verdict = 'OVERVALUED'
    #     ORDER BY margin_of_safety_pct ASC
    # """,

    # "nse_top20_overvalued": """
    #     SELECT TOP 20
    #         ticker,
    #         company_name,
    #         market,
    #         sector,
    #         industry,
    #         implied_current_price,
    #         graham_number,
    #         peg_fair_value,
    #         forward_earnings_value,
    #         earnings_power_value,
    #         composite_fair_value,
    #         margin_of_safety_pct,
    #         valuation_verdict,
    #         trailing_pe,
    #         forward_pe,
    #         price_to_book,
    #         earnings_growth,
    #         return_on_equity,
    #         beta
    #     FROM vw_fair_value_estimates
    #     WHERE market = 'NSE'
    #       AND composite_fair_value IS NOT NULL
    #       AND implied_current_price IS NOT NULL
    #       AND valuation_verdict = 'OVERVALUED'
    #     ORDER BY margin_of_safety_pct ASC
    # """,

    # "sector_valuation_heatmap": """
    #     SELECT
    #         market,
    #         sector,
    #         COUNT(*) AS total_stocks,
    #         SUM(CASE WHEN valuation_verdict IN ('SIGNIFICANTLY UNDERVALUED', 'UNDERVALUED') 
    #             THEN 1 ELSE 0 END) AS undervalued_count,
    #         SUM(CASE WHEN valuation_verdict = 'FAIRLY VALUED' THEN 1 ELSE 0 END) AS fair_count,
    #         SUM(CASE WHEN valuation_verdict = 'OVERVALUED' THEN 1 ELSE 0 END) AS overvalued_count,
    #         ROUND(AVG(margin_of_safety_pct), 2) AS avg_margin_of_safety,
    #         ROUND(AVG(CASE WHEN composite_fair_value IS NOT NULL 
    #             THEN composite_fair_value END), 2) AS avg_fair_value
    #     FROM vw_fair_value_estimates
    #     WHERE composite_fair_value IS NOT NULL
    #       AND implied_current_price IS NOT NULL
    #     GROUP BY market, sector
    #     HAVING COUNT(*) >= 3
    #     ORDER BY market, avg_margin_of_safety DESC
    # """,
}