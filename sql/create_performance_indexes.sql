-- ============================================================================
-- Performance Index Optimization for Stock Data Agentic AI
-- ============================================================================
-- Analysis: These indexes address the specific query patterns used by
-- the 7 AI agents. Each index targets a bottleneck found during testing.
--
-- Run this script once in SSMS against stockdata_db.
-- Safe to run multiple times (IF NOT EXISTS checks).
-- ============================================================================

USE stockdata_db;
GO

PRINT '=== Starting Index Creation ===';
PRINT '';

-- ============================================================================
-- 1. ml_nse_trading_predictions (28,647 rows) - BIGGEST BOTTLENECK
--    Problem: Queries filter by MAX(trading_date) + signal_strength + 
--             high_confidence, then ORDER BY confidence_percentage DESC.
--    Existing: Only has separate indexes on trading_date, predicted_signal,
--              signal_strength individually. No composite covering index.
-- ============================================================================

-- Covering index for the "top signals" query (Agent 4)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_nse_pred_date_strength_conf' AND object_id = OBJECT_ID('ml_nse_trading_predictions'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_nse_pred_date_strength_conf
    ON ml_nse_trading_predictions (trading_date, signal_strength, high_confidence)
    INCLUDE (ticker, company, predicted_signal, confidence_percentage, rsi, rsi_category, 
             buy_probability, sell_probability, close_price, model_name, sector);
    PRINT 'Created: IX_nse_pred_date_strength_conf on ml_nse_trading_predictions';
END
ELSE PRINT 'Skipped: IX_nse_pred_date_strength_conf (already exists)';
GO

-- Covering index for GROUP BY predicted_signal queries (Agent 2 ML summary)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_nse_pred_date_signal_agg' AND object_id = OBJECT_ID('ml_nse_trading_predictions'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_nse_pred_date_signal_agg
    ON ml_nse_trading_predictions (trading_date, predicted_signal)
    INCLUDE (confidence_percentage, signal_strength);
    PRINT 'Created: IX_nse_pred_date_signal_agg on ml_nse_trading_predictions';
END
ELSE PRINT 'Skipped: IX_nse_pred_date_signal_agg (already exists)';
GO

-- ============================================================================
-- 2. ml_trading_predictions (5,041 rows)
--    Problem: Missing single-column trading_date index! Queries use
--    WHERE trading_date = (SELECT MAX(trading_date)) which needs fast MAX.
--    Also missing composite for accuracy queries.
-- ============================================================================

-- Single column for fast MAX(trading_date) lookups
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_trading_pred_date' AND object_id = OBJECT_ID('ml_trading_predictions'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_trading_pred_date
    ON ml_trading_predictions (trading_date DESC);
    PRINT 'Created: IX_trading_pred_date on ml_trading_predictions';
END
ELSE PRINT 'Skipped: IX_trading_pred_date (already exists)';
GO

-- Covering index for top signals query (Agent 4)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_trading_pred_date_strength' AND object_id = OBJECT_ID('ml_trading_predictions'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_trading_pred_date_strength
    ON ml_trading_predictions (trading_date, signal_strength)
    INCLUDE (ticker, company, predicted_signal, confidence_percentage, RSI, rsi_category, 
             buy_probability, sell_probability, close_price);
    PRINT 'Created: IX_trading_pred_date_strength on ml_trading_predictions';
END
ELSE PRINT 'Skipped: IX_trading_pred_date_strength (already exists)';
GO

-- Accuracy tracking index (Agent 2 - model health)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_trading_pred_accuracy' AND object_id = OBJECT_ID('ml_trading_predictions'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_trading_pred_accuracy
    ON ml_trading_predictions (trading_date, direction_correct_1d)
    INCLUDE (predicted_signal, confidence_percentage);
    PRINT 'Created: IX_trading_pred_accuracy on ml_trading_predictions';
END
ELSE PRINT 'Skipped: IX_trading_pred_accuracy (already exists)';
GO

-- ============================================================================
-- 3. ai_prediction_history (45,135 rows)
--    Problem: Queries do GROUP BY model_name WHERE target_date >= -7 days
--    AND actual_price IS NOT NULL. Existing index is (model_name, target_date)
--    but doesn't cover actual_price filter or the aggregate columns.
-- ============================================================================

-- Covering index for 7-day/30-day accuracy queries (Agent 2)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ai_pred_accuracy_cover' AND object_id = OBJECT_ID('ai_prediction_history'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_ai_pred_accuracy_cover
    ON ai_prediction_history (target_date, actual_price)
    INCLUDE (model_name, direction_correct, absolute_error, percentage_error);
    PRINT 'Created: IX_ai_pred_accuracy_cover on ai_prediction_history';
END
ELSE PRINT 'Skipped: IX_ai_pred_accuracy_cover (already exists)';
GO

-- Market-level accuracy (Agent 2 - by market breakdown)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ai_pred_market_accuracy' AND object_id = OBJECT_ID('ai_prediction_history'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_ai_pred_market_accuracy
    ON ai_prediction_history (target_date, market)
    INCLUDE (model_name, direction_correct, absolute_error);
    PRINT 'Created: IX_ai_pred_market_accuracy on ai_prediction_history';
END
ELSE PRINT 'Skipped: IX_ai_pred_market_accuracy (already exists)';
GO

-- ============================================================================
-- 4. signal_tracking_history (20,633 rows)
--    Problem: View vw_PowerBI_AI_Technical_Combos joins this with
--    ai_prediction_history on (market, ticker, signal_date).
--    Also: Agents query by signal_date with GROUP BY signal_type.
-- ============================================================================

-- Composite for view join performance
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_signal_market_date_ticker' AND object_id = OBJECT_ID('signal_tracking_history'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_signal_market_date_ticker
    ON signal_tracking_history (market, signal_date, ticker)
    INCLUDE (signal_type, signal_strength, signal_price, macd_signal, rsi_signal,
             bb_signal, stoch_signal, fib_signal, pattern_signal,
             result_7d, actual_change_7d, company_name);
    PRINT 'Created: IX_signal_market_date_ticker on signal_tracking_history';
END
ELSE PRINT 'Skipped: IX_signal_market_date_ticker (already exists)';
GO

-- For signal outcome accuracy queries (Agent 3)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_signal_date_type_results' AND object_id = OBJECT_ID('signal_tracking_history'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_signal_date_type_results
    ON signal_tracking_history (signal_date, signal_type)
    INCLUDE (result_7d, actual_change_7d, result_14d, actual_change_14d);
    PRINT 'Created: IX_signal_date_type_results on signal_tracking_history';
END
ELSE PRINT 'Skipped: IX_signal_date_type_results (already exists)';
GO

-- ============================================================================
-- 5. nasdaq_100_hist_data (127,889 rows)
--    Problem: No single-column index on trading_date! Every agent query
--    does WHERE trading_date = (SELECT MAX(trading_date)...) which scans
--    the entire ticker+date composite index to find the max date.
-- ============================================================================

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_nasdaq_hist_trading_date' AND object_id = OBJECT_ID('nasdaq_100_hist_data'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_nasdaq_hist_trading_date
    ON nasdaq_100_hist_data (trading_date DESC)
    INCLUDE (ticker, company, open_price, close_price, volume);
    PRINT 'Created: IX_nasdaq_hist_trading_date on nasdaq_100_hist_data';
END
ELSE PRINT 'Skipped: IX_nasdaq_hist_trading_date (already exists)';
GO

-- ============================================================================
-- 6. nse_500_hist_data (509,799 rows) - SECOND BIGGEST TABLE
--    Problem: Same as NASDAQ - no single-column trading_date index.
--    With 500k rows, the MAX(trading_date) subquery is very expensive.
-- ============================================================================

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_nse_hist_trading_date' AND object_id = OBJECT_ID('nse_500_hist_data'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_nse_hist_trading_date
    ON nse_500_hist_data (trading_date DESC)
    INCLUDE (ticker, company, open_price, close_price, volume);
    PRINT 'Created: IX_nse_hist_trading_date on nse_500_hist_data';
END
ELSE PRINT 'Skipped: IX_nse_hist_trading_date (already exists)';
GO

-- ============================================================================
-- 7. forex_ml_predictions (290 rows - small but missing key index)
--    Problem: Queries filter by MAX(prediction_date) but no index on
--    prediction_date. Only has index on (currency_pair, date_time).
-- ============================================================================

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_forex_pred_date' AND object_id = OBJECT_ID('forex_ml_predictions'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_forex_pred_date
    ON forex_ml_predictions (prediction_date DESC)
    INCLUDE (currency_pair, predicted_signal, signal_confidence, prob_buy, prob_sell, prob_hold,
             model_name, model_version, close_price);
    PRINT 'Created: IX_forex_pred_date on forex_ml_predictions';
END
ELSE PRINT 'Skipped: IX_forex_pred_date (already exists)';
GO

-- Accuracy tracking for forex
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_forex_pred_accuracy' AND object_id = OBJECT_ID('forex_ml_predictions'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_forex_pred_accuracy
    ON forex_ml_predictions (prediction_date, direction_correct_1d)
    INCLUDE (predicted_signal, signal_confidence);
    PRINT 'Created: IX_forex_pred_accuracy on forex_ml_predictions';
END
ELSE PRINT 'Skipped: IX_forex_pred_accuracy (already exists)';
GO

-- ============================================================================
-- 8. Update statistics on all affected tables
-- ============================================================================

PRINT '';
PRINT '=== Updating Statistics ===';

UPDATE STATISTICS ml_nse_trading_predictions WITH FULLSCAN;
PRINT 'Updated stats: ml_nse_trading_predictions';

UPDATE STATISTICS ml_trading_predictions WITH FULLSCAN;
PRINT 'Updated stats: ml_trading_predictions';

UPDATE STATISTICS ai_prediction_history WITH FULLSCAN;
PRINT 'Updated stats: ai_prediction_history';

UPDATE STATISTICS signal_tracking_history WITH FULLSCAN;
PRINT 'Updated stats: signal_tracking_history';

UPDATE STATISTICS nasdaq_100_hist_data WITH FULLSCAN;
PRINT 'Updated stats: nasdaq_100_hist_data';

UPDATE STATISTICS nse_500_hist_data WITH FULLSCAN;
PRINT 'Updated stats: nse_500_hist_data';

UPDATE STATISTICS forex_ml_predictions WITH FULLSCAN;
PRINT 'Updated stats: forex_ml_predictions';

PRINT '';
PRINT '=== Index Creation Complete ===';
PRINT 'Total new indexes: 13 (if all created)';
PRINT 'Run time should improve significantly for:';
PRINT '  - ml_nse_trading_predictions: GROUP BY and TOP N queries';
PRINT '  - nasdaq/nse_500_hist_data: MAX(trading_date) lookups';
PRINT '  - ai_prediction_history: Accuracy aggregation queries';
PRINT '  - signal_tracking_history: View joins and outcome queries';
GO
