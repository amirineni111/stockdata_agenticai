-- ===========================================================================
-- CONSOLIDATED CROSS-STRATEGY QUERIES (2 queries instead of 8)
-- This reduces API calls from 8 to 2, speeding up execution and saving credits
-- ===========================================================================

-- Query 1: NSE 500 - All 4 Categories in One Query
-- ===========================================================================
nse_all_categories:
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


-- Query 2: NASDAQ 100 - All 4 Categories in One Query
-- ===========================================================================
nasdaq_all_categories:
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
