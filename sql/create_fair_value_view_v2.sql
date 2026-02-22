-- =============================================================================
-- Fair Value Estimates View v2 — Refactored with outlier protection
-- =============================================================================
-- FIXES from v1:
--   1. PEG Fair Value: cap earnings_growth at 1.0 (100%); exclude above that
--   2. Refactored to use CTE for per-model values (eliminates 4x repetition)
--   3. Composite Fair Value capped at 10x implied price as safety net
--   4. Cleaner, more maintainable structure
-- =============================================================================
-- Dependencies: nasdaq_100_fundamentals, nse_500_fundamentals,
--               nasdaq_top100, nse_500
-- =============================================================================

CREATE OR ALTER VIEW vw_fair_value_estimates AS
WITH latest_fundamentals AS (
    -- NSE stocks
    SELECT 
        f.ticker, f.company_name, f.fetch_date,
        n.sector, n.industry,
        'NSE' AS market,
        f.market_cap, f.trailing_pe, f.forward_pe, f.price_to_book,
        f.peg_ratio, f.trailing_eps, f.forward_eps, f.book_value,
        f.earnings_growth, f.revenue_growth, f.return_on_equity,
        f.return_on_assets, f.free_cashflow, f.operating_cashflow,
        f.beta, f.fifty_two_week_high, f.fifty_two_week_low,
        f.fifty_day_avg, f.two_hundred_day_avg,
        f.profit_margin, f.debt_to_equity, f.dividend_yield,
        ROW_NUMBER() OVER (PARTITION BY f.ticker ORDER BY f.fetch_date DESC) AS rn
    FROM nse_500_fundamentals f
    INNER JOIN nse_500 n ON f.ticker = n.ticker

    UNION ALL

    -- NASDAQ stocks
    SELECT 
        f.ticker, f.company_name, f.fetch_date,
        q.sector, q.industry,
        'NASDAQ' AS market,
        f.market_cap, f.trailing_pe, f.forward_pe, f.price_to_book,
        f.peg_ratio, f.trailing_eps, f.forward_eps, f.book_value,
        f.earnings_growth, f.revenue_growth, f.return_on_equity,
        f.return_on_assets, f.free_cashflow, f.operating_cashflow,
        f.beta, f.fifty_two_week_high, f.fifty_two_week_low,
        f.fifty_day_avg, f.two_hundred_day_avg,
        f.profit_margin, f.debt_to_equity, f.dividend_yield,
        ROW_NUMBER() OVER (PARTITION BY f.ticker ORDER BY f.fetch_date DESC) AS rn
    FROM nasdaq_100_fundamentals f
    INNER JOIN nasdaq_top100 q ON f.ticker = q.ticker
),
current_fundamentals AS (
    SELECT * FROM latest_fundamentals WHERE rn = 1
),
sector_averages AS (
    SELECT 
        market, sector,
        AVG(forward_pe)  AS sector_avg_forward_pe,
        AVG(trailing_pe) AS sector_avg_trailing_pe,
        COUNT(*)         AS stocks_in_sector
    FROM current_fundamentals
    WHERE forward_pe > 0 AND forward_pe < 100
      AND trailing_pe > 0 AND trailing_pe < 100
    GROUP BY market, sector
),
-- =========================================================================
-- NEW: Compute individual model values in a CTE to avoid 4x repetition
-- =========================================================================
model_values AS (
    SELECT
        cf.*,
        sa.sector_avg_forward_pe,
        sa.sector_avg_trailing_pe,
        sa.stocks_in_sector,

        -- Implied current price (EPS × P/E proxy)
        CASE WHEN cf.trailing_eps > 0 AND cf.trailing_pe > 0
             THEN ROUND(cf.trailing_eps * cf.trailing_pe, 2)
        END AS implied_current_price,

        -- Model 1: Graham Number = sqrt(22.5 × EPS × Book Value)
        CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0
             THEN ROUND(SQRT(22.5 * cf.trailing_eps * cf.book_value), 2)
        END AS graham_number,

        -- Model 2: PEG Fair Value = Forward EPS × min(earnings_growth, 1.0) × 100
        -- FIX: Cap earnings_growth at 1.0 (100%). Above 100% growth,
        --       the PEG=1.0 heuristic breaks down and produces nonsense.
        --       Stocks with growth > 100% use capped rate of 100%.
        CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0
             THEN ROUND(cf.forward_eps
                  * IIF(cf.earnings_growth > 1.0, 1.0, cf.earnings_growth)
                  * 100, 2)
        END AS peg_fair_value,

        -- Model 3: Forward Earnings Value = Forward EPS × Sector Avg P/E
        CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0
             THEN ROUND(cf.forward_eps * sa.sector_avg_forward_pe, 2)
        END AS forward_earnings_value,

        -- Model 4: EPV = EPS × (1 - 21% tax) / 10% WACC
        CASE WHEN cf.trailing_eps > 0
             THEN ROUND(cf.trailing_eps * 0.79 / 0.10, 2)
        END AS earnings_power_value

    FROM current_fundamentals cf
    LEFT JOIN sector_averages sa
        ON cf.market = sa.market AND cf.sector = sa.sector
),
-- =========================================================================
-- Compute composite fair value from the model CTE
-- =========================================================================
composites AS (
    SELECT
        mv.*,

        -- Number of models that produced a value
        (CASE WHEN mv.graham_number           IS NOT NULL THEN 1 ELSE 0 END
       + CASE WHEN mv.peg_fair_value          IS NOT NULL THEN 1 ELSE 0 END
       + CASE WHEN mv.forward_earnings_value  IS NOT NULL THEN 1 ELSE 0 END
       + CASE WHEN mv.earnings_power_value    IS NOT NULL THEN 1 ELSE 0 END)
        AS model_count,

        -- Raw composite = average of available models
        CASE WHEN
            (CASE WHEN mv.graham_number          IS NOT NULL THEN 1 ELSE 0 END
           + CASE WHEN mv.peg_fair_value         IS NOT NULL THEN 1 ELSE 0 END
           + CASE WHEN mv.forward_earnings_value IS NOT NULL THEN 1 ELSE 0 END
           + CASE WHEN mv.earnings_power_value   IS NOT NULL THEN 1 ELSE 0 END) > 0
        THEN
            ROUND(
                (COALESCE(mv.graham_number, 0)
               + COALESCE(mv.peg_fair_value, 0)
               + COALESCE(mv.forward_earnings_value, 0)
               + COALESCE(mv.earnings_power_value, 0))
            * 1.0
            / (CASE WHEN mv.graham_number          IS NOT NULL THEN 1 ELSE 0 END
             + CASE WHEN mv.peg_fair_value         IS NOT NULL THEN 1 ELSE 0 END
             + CASE WHEN mv.forward_earnings_value IS NOT NULL THEN 1 ELSE 0 END
             + CASE WHEN mv.earnings_power_value   IS NOT NULL THEN 1 ELSE 0 END)
            , 2)
        END AS raw_composite

    FROM model_values mv
)
-- Final SELECT with capped composite, margin of safety, and verdict
SELECT
    c.ticker,
    c.company_name,
    c.market,
    c.sector,
    c.industry,
    c.fetch_date,

    c.implied_current_price,
    c.graham_number,
    c.peg_fair_value,
    c.forward_earnings_value,
    c.earnings_power_value,

    -- FIX: Cap composite at 10× implied price as a safety net
    CASE
        WHEN c.raw_composite IS NULL THEN NULL
        WHEN c.implied_current_price IS NOT NULL
             AND c.raw_composite > c.implied_current_price * 10
        THEN ROUND(c.implied_current_price * 10, 2)
        ELSE c.raw_composite
    END AS composite_fair_value,

    -- Margin of Safety using capped composite
    CASE WHEN c.implied_current_price > 0 AND c.raw_composite IS NOT NULL
         THEN ROUND(
            (IIF(c.implied_current_price IS NOT NULL
                 AND c.raw_composite > c.implied_current_price * 10,
                 c.implied_current_price * 10,
                 c.raw_composite)
             - c.implied_current_price)
            / NULLIF(
                IIF(c.implied_current_price IS NOT NULL
                    AND c.raw_composite > c.implied_current_price * 10,
                    c.implied_current_price * 10,
                    c.raw_composite)
              , 0)
            * 100, 2)
    END AS margin_of_safety_pct,

    -- Valuation Verdict using capped composite
    CASE
        WHEN c.implied_current_price IS NULL OR c.raw_composite IS NULL
            THEN 'INSUFFICIENT DATA'
        WHEN IIF(c.raw_composite > c.implied_current_price * 10,
                 c.implied_current_price * 10, c.raw_composite)
             >= c.implied_current_price * 1.30
            THEN 'SIGNIFICANTLY UNDERVALUED'
        WHEN IIF(c.raw_composite > c.implied_current_price * 10,
                 c.implied_current_price * 10, c.raw_composite)
             >= c.implied_current_price * 1.10
            THEN 'UNDERVALUED'
        WHEN IIF(c.raw_composite > c.implied_current_price * 10,
                 c.implied_current_price * 10, c.raw_composite)
             >= c.implied_current_price * 0.90
            THEN 'FAIRLY VALUED'
        ELSE 'OVERVALUED'
    END AS valuation_verdict,

    -- Supporting metrics
    c.sector_avg_forward_pe,
    c.sector_avg_trailing_pe,
    c.stocks_in_sector,
    c.trailing_pe,
    c.forward_pe,
    c.price_to_book,
    c.peg_ratio,
    c.trailing_eps,
    c.forward_eps,
    c.book_value,
    c.earnings_growth,
    c.revenue_growth,
    c.return_on_equity,
    c.profit_margin,
    c.debt_to_equity,
    c.beta,
    c.dividend_yield,
    c.fifty_two_week_high,
    c.fifty_two_week_low,
    c.fifty_day_avg,
    c.two_hundred_day_avg

FROM composites c;
GO
