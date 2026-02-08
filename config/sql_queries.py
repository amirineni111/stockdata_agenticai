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
        ORDER BY model_confidence DESC
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
            AND signal_date = (
                SELECT MAX(signal_date) FROM vw_PowerBI_AI_Technical_Combos
                WHERE market = 'NSE 500'
            )
        ORDER BY signal_strength DESC, ABS(ai_prediction_pct) DESC
    """,
}

# =============================================================================
# Agent 5: Forex Analysis Agent Queries
# =============================================================================

FOREX_QUERIES = {
    "forex_latest_rates": """
        SELECT
            symbol,
            currency_from,
            currency_to,
            trading_date,
            open_price,
            high_price,
            low_price,
            close_price,
            daily_change,
            daily_change_pct,
            fifty_day_avg,
            two_hundred_day_avg
        FROM forex_hist_data
        WHERE trading_date = (
            SELECT MAX(trading_date) FROM forex_hist_data
        )
        ORDER BY symbol
    """,

    "forex_ml_predictions_latest": """
        SELECT TOP 5
            currency_pair,
            prediction_date,
            close_price,
            predicted_signal,
            signal_confidence,
            prob_buy,
            prob_sell,
            prob_hold,
            model_name,
            model_version
        FROM forex_ml_predictions
        WHERE prediction_date = (
            SELECT MAX(prediction_date) FROM forex_ml_predictions
        )
        ORDER BY signal_confidence DESC
    """,

    "forex_weekly_trend": """
        SELECT
            symbol,
            MIN(close_price) AS week_low,
            MAX(close_price) AS week_high,
            (SELECT TOP 1 close_price FROM forex_hist_data f2
             WHERE f2.symbol = f1.symbol
             ORDER BY f2.trading_date ASC) AS week_open,
            (SELECT TOP 1 close_price FROM forex_hist_data f3
             WHERE f3.symbol = f1.symbol
             ORDER BY f3.trading_date DESC) AS week_close
        FROM forex_hist_data f1
        WHERE trading_date >= DATEADD(DAY, -7, GETDATE())
        GROUP BY symbol
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
        SELECT
            ticker,
            market,
            company_name,
            ai_direction,
            predicted_change_pct,
            ai_confidence,
            system_agreement,
            risk_level,
            risk_reward_ratio,
            warning_flag,
            current_price,
            stop_loss_price,
            model_disagreement
        FROM strategy1_tracking
        WHERE risk_level = 'HIGH'
            AND report_date = (
                SELECT MAX(report_date) FROM strategy1_tracking
            )
        ORDER BY model_disagreement DESC
    """,

    "conflicting_signals": """
        SELECT
            ticker,
            market,
            company_name,
            ai_direction,
            tech_direction,
            ai_confidence,
            tech_score,
            model_disagreement,
            warning_flag,
            current_price
        FROM strategy1_tracking
        WHERE system_agreement = 'CONFLICTING'
            AND report_date = (
                SELECT MAX(report_date) FROM strategy1_tracking
            )
        ORDER BY model_disagreement DESC
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
    "common_stocks_both_strategies": """
        WITH s1_best AS (
            SELECT
                s1.market,
                s1.ticker,
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
                SELECT market, MAX(signal_date) AS max_date
                FROM vw_PowerBI_AI_Technical_Combos
                GROUP BY market
            ) latest ON s1.market = latest.market AND s1.signal_date = latest.max_date
            WHERE s1.trade_tier LIKE 'TIER 1%'
        )
        SELECT
            s2.market,
            s1b.ticker,
            s2.company,
            s1b.signal_type AS s1_direction,
            s1b.trade_tier AS s1_tier,
            s1b.ai_prediction_pct AS s1_ai_pct,
            s1b.technical_combo AS s1_tech_combo,
            s2.ml_signal AS s2_signal,
            s2.trade_grade AS s2_grade,
            ROUND(s2.ml_confidence_pct, 1) AS s2_confidence_pct,
            s2.opportunity_score AS s2_score,
            s2.recommended_action AS s2_action,
            CASE
                WHEN (s1b.signal_type = 'BEARISH' AND s2.ml_signal = 'Sell')
                  OR (s1b.signal_type = 'BULLISH' AND s2.ml_signal = 'Buy')
                THEN 'ALIGNED'
                ELSE 'CONFLICTING'
            END AS cross_strategy_agreement
        FROM vw_strategy2_trade_opportunities s2
        INNER JOIN s1_best s1b ON s2.ticker = s1b.ticker AND s1b.rn = 1
        WHERE s2.prediction_date = (
            SELECT MAX(prediction_date) FROM vw_strategy2_trade_opportunities
            WHERE market IN ('NASDAQ', 'NSE')
        )
        AND s2.trade_grade IN ('A - STRONG SHORT', 'A - STRONG LONG', 'B - GOOD SHORT', 'B - GOOD LONG')
        ORDER BY s2_confidence_pct DESC
    """,

    "common_stocks_summary": """
        WITH s1_best AS (
            SELECT
                s1.ticker,
                s1.signal_type,
                ROW_NUMBER() OVER (
                    PARTITION BY s1.ticker
                    ORDER BY ABS(CAST(s1.ai_prediction_pct AS FLOAT)) DESC
                ) AS rn
            FROM vw_PowerBI_AI_Technical_Combos s1
            INNER JOIN (
                SELECT market, MAX(signal_date) AS max_date
                FROM vw_PowerBI_AI_Technical_Combos
                GROUP BY market
            ) latest ON s1.market = latest.market AND s1.signal_date = latest.max_date
            WHERE s1.trade_tier LIKE 'TIER 1%'
        )
        SELECT
            cross_agreement,
            COUNT(*) AS total_stocks,
            ROUND(AVG(s2_confidence), 1) AS avg_s2_confidence
        FROM (
            SELECT
                s2.ticker,
                ROUND(s2.ml_confidence_pct, 1) AS s2_confidence,
                CASE
                    WHEN (s1b.signal_type = 'BEARISH' AND s2.ml_signal = 'Sell')
                      OR (s1b.signal_type = 'BULLISH' AND s2.ml_signal = 'Buy')
                    THEN 'ALIGNED'
                    ELSE 'CONFLICTING'
                END AS cross_agreement
            FROM vw_strategy2_trade_opportunities s2
            INNER JOIN s1_best s1b ON s2.ticker = s1b.ticker AND s1b.rn = 1
            WHERE s2.prediction_date = (
                SELECT MAX(prediction_date) FROM vw_strategy2_trade_opportunities
                WHERE market IN ('NASDAQ', 'NSE')
            )
            AND s2.trade_grade IN ('A - STRONG SHORT', 'A - STRONG LONG', 'B - GOOD SHORT', 'B - GOOD LONG')
        ) sub
        GROUP BY cross_agreement
    """,

    "forex_strategy2_signals": """
        SELECT TOP 10
            ticker,
            company,
            ml_signal,
            ml_direction,
            ROUND(ml_confidence_pct, 1) AS confidence_pct,
            trade_grade,
            opportunity_score,
            recommended_action,
            rsi_category
        FROM vw_strategy2_trade_opportunities
        WHERE market = 'Forex'
            AND prediction_date = (
                SELECT MAX(prediction_date) FROM vw_strategy2_trade_opportunities
                WHERE market = 'Forex'
            )
        ORDER BY opportunity_score DESC, ml_confidence_pct DESC
    """,
}
