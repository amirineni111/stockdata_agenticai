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
        SELECT TOP 5
            market,
            ticker,
            company_name,
            signal_date,
            signal_type,
            signal_strength,
            signal_status,
            signal_price,
            macd_signal,
            rsi_signal,
            bb_signal,
            sma_signal,
            stoch_signal,
            fib_signal,
            pattern_signal
        FROM signal_tracking_history
        WHERE signal_date = (
            SELECT MAX(signal_date) FROM signal_tracking_history
        )
        ORDER BY signal_strength DESC
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
        SELECT TOP 5
            market,
            ticker,
            company_name,
            signal_date,
            signal_type,
            signal_strength,
            signal_price,
            macd_signal,
            rsi_signal,
            stoch_signal,
            fib_signal,
            pattern_signal
        FROM signal_tracking_history
        WHERE signal_date >= DATEADD(DAY, -3, GETDATE())
            AND signal_strength >= 3
        ORDER BY signal_strength DESC, signal_date DESC
    """,
}

# =============================================================================
# Agent 4: Strategy & Trade Agent Queries
# =============================================================================

STRATEGY_TRADE_QUERIES = {
    "top_tier1_opportunities": """
        SELECT TOP 10
            ticker,
            market,
            company_name,
            prediction_date,
            ai_direction,
            predicted_change_pct,
            ai_confidence,
            tech_direction,
            tech_score,
            system_agreement,
            combined_score,
            trade_tier,
            stop_loss_price,
            take_profit_price,
            position_size_pct,
            risk_level,
            risk_reward_ratio,
            current_price,
            warning_flag
        FROM strategy1_tracking
        WHERE trade_tier = 'TIER 1'
            AND report_date = (
                SELECT MAX(report_date) FROM strategy1_tracking
            )
        ORDER BY combined_score DESC
    """,

    "top_tier2_opportunities": """
        SELECT TOP 5
            ticker,
            market,
            company_name,
            prediction_date,
            ai_direction,
            predicted_change_pct,
            ai_confidence,
            tech_direction,
            tech_score,
            system_agreement,
            combined_score,
            trade_tier,
            stop_loss_price,
            take_profit_price,
            position_size_pct,
            risk_level,
            risk_reward_ratio,
            current_price,
            warning_flag
        FROM strategy1_tracking
        WHERE trade_tier = 'TIER 2'
            AND report_date = (
                SELECT MAX(report_date) FROM strategy1_tracking
            )
        ORDER BY combined_score DESC
    """,

    "aligned_signals_today": """
        SELECT
            ticker,
            market,
            company_name,
            ai_direction,
            predicted_change_pct,
            ai_confidence,
            tech_direction,
            tech_score,
            combined_score,
            trade_tier,
            risk_reward_ratio,
            current_price
        FROM strategy1_tracking
        WHERE system_agreement = 'ALIGNED'
            AND report_date = (
                SELECT MAX(report_date) FROM strategy1_tracking
            )
        ORDER BY combined_score DESC
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

    "strategy_performance_summary": """
        SELECT
            trade_tier,
            COUNT(*) AS total_opportunities,
            SUM(CASE WHEN system_agreement = 'ALIGNED' THEN 1 ELSE 0 END) AS aligned_count,
            SUM(CASE WHEN system_agreement = 'CONFLICTING' THEN 1 ELSE 0 END) AS conflicting_count,
            ROUND(AVG(combined_score), 1) AS avg_combined_score,
            ROUND(AVG(ai_confidence), 1) AS avg_ai_confidence,
            ROUND(AVG(risk_reward_ratio), 2) AS avg_risk_reward
        FROM strategy1_tracking
        WHERE report_date = (
            SELECT MAX(report_date) FROM strategy1_tracking
        )
        GROUP BY trade_tier
        ORDER BY trade_tier
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
