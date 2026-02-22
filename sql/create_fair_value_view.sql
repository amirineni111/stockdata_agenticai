-- =============================================================================
-- Fair Value Estimates View
-- Computes 4 fair value models per stock using fundamentals data from yfinance
-- Models: Graham Number, PEG Fair Value, Forward Earnings Value, EPV
-- =============================================================================
-- Usage: Run this on stockdata_db to create the view
-- Dependencies: nasdaq_100_fundamentals, nse_500_fundamentals,
--               nasdaq_top100, nse_500
-- =============================================================================

CREATE OR ALTER VIEW vw_fair_value_estimates AS
WITH latest_fundamentals AS (
    -- NSE stocks: join with nse_500 for sector/industry
    SELECT 
        f.ticker,
        f.company_name,
        f.fetch_date,
        n.sector,
        n.industry,
        'NSE' AS market,
        f.market_cap,
        f.trailing_pe,
        f.forward_pe,
        f.price_to_book,
        f.peg_ratio,
        f.trailing_eps,
        f.forward_eps,
        f.book_value,
        f.earnings_growth,
        f.revenue_growth,
        f.return_on_equity,
        f.return_on_assets,
        f.free_cashflow,
        f.operating_cashflow,
        f.beta,
        f.fifty_two_week_high,
        f.fifty_two_week_low,
        f.fifty_day_avg,
        f.two_hundred_day_avg,
        f.profit_margin,
        f.debt_to_equity,
        f.dividend_yield,
        ROW_NUMBER() OVER (PARTITION BY f.ticker ORDER BY f.fetch_date DESC) AS rn
    FROM nse_500_fundamentals f
    INNER JOIN nse_500 n ON f.ticker = n.ticker

    UNION ALL

    -- NASDAQ stocks: join with nasdaq_top100 for sector/industry
    SELECT 
        f.ticker,
        f.company_name,
        f.fetch_date,
        q.sector,
        q.industry,
        'NASDAQ' AS market,
        f.market_cap,
        f.trailing_pe,
        f.forward_pe,
        f.price_to_book,
        f.peg_ratio,
        f.trailing_eps,
        f.forward_eps,
        f.book_value,
        f.earnings_growth,
        f.revenue_growth,
        f.return_on_equity,
        f.return_on_assets,
        f.free_cashflow,
        f.operating_cashflow,
        f.beta,
        f.fifty_two_week_high,
        f.fifty_two_week_low,
        f.fifty_day_avg,
        f.two_hundred_day_avg,
        f.profit_margin,
        f.debt_to_equity,
        f.dividend_yield,
        ROW_NUMBER() OVER (PARTITION BY f.ticker ORDER BY f.fetch_date DESC) AS rn
    FROM nasdaq_100_fundamentals f
    INNER JOIN nasdaq_top100 q ON f.ticker = q.ticker
),
-- Only keep the most recent fundamentals row per ticker
current_fundamentals AS (
    SELECT * FROM latest_fundamentals WHERE rn = 1
),
-- Compute sector average P/E for Forward Earnings Value model
sector_averages AS (
    SELECT 
        market,
        sector,
        AVG(forward_pe)   AS sector_avg_forward_pe,
        AVG(trailing_pe)  AS sector_avg_trailing_pe,
        COUNT(*)           AS stocks_in_sector
    FROM current_fundamentals
    WHERE forward_pe > 0 AND forward_pe < 100   -- exclude outliers
      AND trailing_pe > 0 AND trailing_pe < 100
    GROUP BY market, sector
)
SELECT 
    cf.ticker,
    cf.company_name,
    cf.market,
    cf.sector,
    cf.industry,
    cf.fetch_date,

    -- =========================================================================
    -- Current Price Proxy (EPS × P/E since we don't have live price in this table)
    -- =========================================================================
    CASE WHEN cf.trailing_eps > 0 AND cf.trailing_pe > 0
         THEN ROUND(cf.trailing_eps * cf.trailing_pe, 2)
    END AS implied_current_price,

    -- =========================================================================
    -- Model 1: Graham Number = sqrt(22.5 × EPS × Book Value)
    -- Conservative intrinsic value for defensive investors
    -- =========================================================================
    CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0
         THEN ROUND(SQRT(22.5 * cf.trailing_eps * cf.book_value), 2)
    END AS graham_number,

    -- =========================================================================
    -- Model 2: PEG Fair Value = Forward EPS × Earnings Growth Rate × 100
    -- Fair P/E should equal growth rate (PEG = 1.0)
    -- =========================================================================
    CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0
         THEN ROUND(cf.forward_eps * cf.earnings_growth * 100, 2)
    END AS peg_fair_value,

    -- =========================================================================
    -- Model 3: Forward Earnings Value = Forward EPS × Sector Avg P/E
    -- What the stock "should" trade at given sector norms
    -- =========================================================================
    CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0
         THEN ROUND(cf.forward_eps * sa.sector_avg_forward_pe, 2)
    END AS forward_earnings_value,

    -- =========================================================================
    -- Model 4: Earnings Power Value = EPS × (1 - Tax Rate) / WACC
    -- Values the business as-is with no growth assumptions
    -- Uses 21% corporate tax rate and 10% discount rate (WACC proxy)
    -- =========================================================================
    CASE WHEN cf.trailing_eps > 0
         THEN ROUND(cf.trailing_eps * 0.79 / 0.10, 2)
    END AS earnings_power_value,

    -- =========================================================================
    -- Composite Fair Value = Average of all available models
    -- =========================================================================
    ROUND(
        (COALESCE(
            CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0
                 THEN SQRT(22.5 * cf.trailing_eps * cf.book_value) END, 0)
        + COALESCE(
            CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0
                 THEN cf.forward_eps * cf.earnings_growth * 100 END, 0)
        + COALESCE(
            CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0
                 THEN cf.forward_eps * sa.sector_avg_forward_pe END, 0)
        + COALESCE(
            CASE WHEN cf.trailing_eps > 0
                 THEN cf.trailing_eps * 0.79 / 0.10 END, 0)
        )
        -- Divide by number of models that produced a value
        / NULLIF(
            CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0 THEN 1 ELSE 0 END
          + CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0 THEN 1 ELSE 0 END
          + CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0 THEN 1 ELSE 0 END
          + CASE WHEN cf.trailing_eps > 0 THEN 1 ELSE 0 END
        , 0)
    , 2) AS composite_fair_value,

    -- =========================================================================
    -- Margin of Safety % = (Fair Value - Current Price) / Fair Value × 100
    -- Positive = undervalued, Negative = overvalued
    -- =========================================================================
    CASE WHEN cf.trailing_eps > 0 AND cf.trailing_pe > 0
         THEN ROUND(
            (
                -- Composite fair value (repeated for the margin calc)
                (COALESCE(
                    CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0
                         THEN SQRT(22.5 * cf.trailing_eps * cf.book_value) END, 0)
                + COALESCE(
                    CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0
                         THEN cf.forward_eps * cf.earnings_growth * 100 END, 0)
                + COALESCE(
                    CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0
                         THEN cf.forward_eps * sa.sector_avg_forward_pe END, 0)
                + COALESCE(
                    CASE WHEN cf.trailing_eps > 0
                         THEN cf.trailing_eps * 0.79 / 0.10 END, 0)
                )
                / NULLIF(
                    CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0 THEN 1 ELSE 0 END
                  + CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0 THEN 1 ELSE 0 END
                  + CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0 THEN 1 ELSE 0 END
                  + CASE WHEN cf.trailing_eps > 0 THEN 1 ELSE 0 END
                , 0)
                -- Minus implied price
                - (cf.trailing_eps * cf.trailing_pe)
            )
            / NULLIF(
                (COALESCE(
                    CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0
                         THEN SQRT(22.5 * cf.trailing_eps * cf.book_value) END, 0)
                + COALESCE(
                    CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0
                         THEN cf.forward_eps * cf.earnings_growth * 100 END, 0)
                + COALESCE(
                    CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0
                         THEN cf.forward_eps * sa.sector_avg_forward_pe END, 0)
                + COALESCE(
                    CASE WHEN cf.trailing_eps > 0
                         THEN cf.trailing_eps * 0.79 / 0.10 END, 0)
                )
                / NULLIF(
                    CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0 THEN 1 ELSE 0 END
                  + CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0 THEN 1 ELSE 0 END
                  + CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0 THEN 1 ELSE 0 END
                  + CASE WHEN cf.trailing_eps > 0 THEN 1 ELSE 0 END
                , 0)
            , 0) * 100
         , 2)
    END AS margin_of_safety_pct,

    -- =========================================================================
    -- Valuation Verdict
    -- =========================================================================
    CASE 
        WHEN cf.trailing_eps <= 0 OR cf.trailing_pe <= 0 THEN 'INSUFFICIENT DATA'
        WHEN (
            (COALESCE(
                CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0
                     THEN SQRT(22.5 * cf.trailing_eps * cf.book_value) END, 0)
            + COALESCE(
                CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0
                     THEN cf.forward_eps * cf.earnings_growth * 100 END, 0)
            + COALESCE(
                CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0
                     THEN cf.forward_eps * sa.sector_avg_forward_pe END, 0)
            + COALESCE(
                CASE WHEN cf.trailing_eps > 0
                     THEN cf.trailing_eps * 0.79 / 0.10 END, 0)
            )
            / NULLIF(
                CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0 THEN 1 ELSE 0 END
              + CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0 THEN 1 ELSE 0 END
              + CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0 THEN 1 ELSE 0 END
              + CASE WHEN cf.trailing_eps > 0 THEN 1 ELSE 0 END
            , 0)
        ) >= (cf.trailing_eps * cf.trailing_pe) * 1.30 THEN 'SIGNIFICANTLY UNDERVALUED'
        WHEN (
            (COALESCE(
                CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0
                     THEN SQRT(22.5 * cf.trailing_eps * cf.book_value) END, 0)
            + COALESCE(
                CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0
                     THEN cf.forward_eps * cf.earnings_growth * 100 END, 0)
            + COALESCE(
                CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0
                     THEN cf.forward_eps * sa.sector_avg_forward_pe END, 0)
            + COALESCE(
                CASE WHEN cf.trailing_eps > 0
                     THEN cf.trailing_eps * 0.79 / 0.10 END, 0)
            )
            / NULLIF(
                CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0 THEN 1 ELSE 0 END
              + CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0 THEN 1 ELSE 0 END
              + CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0 THEN 1 ELSE 0 END
              + CASE WHEN cf.trailing_eps > 0 THEN 1 ELSE 0 END
            , 0)
        ) >= (cf.trailing_eps * cf.trailing_pe) * 1.10 THEN 'UNDERVALUED'
        WHEN (
            (COALESCE(
                CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0
                     THEN SQRT(22.5 * cf.trailing_eps * cf.book_value) END, 0)
            + COALESCE(
                CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0
                     THEN cf.forward_eps * cf.earnings_growth * 100 END, 0)
            + COALESCE(
                CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0
                     THEN cf.forward_eps * sa.sector_avg_forward_pe END, 0)
            + COALESCE(
                CASE WHEN cf.trailing_eps > 0
                     THEN cf.trailing_eps * 0.79 / 0.10 END, 0)
            )
            / NULLIF(
                CASE WHEN cf.trailing_eps > 0 AND cf.book_value > 0 THEN 1 ELSE 0 END
              + CASE WHEN cf.forward_eps > 0 AND cf.earnings_growth > 0 THEN 1 ELSE 0 END
              + CASE WHEN cf.forward_eps > 0 AND sa.sector_avg_forward_pe > 0 THEN 1 ELSE 0 END
              + CASE WHEN cf.trailing_eps > 0 THEN 1 ELSE 0 END
            , 0)
        ) >= (cf.trailing_eps * cf.trailing_pe) * 0.90 THEN 'FAIRLY VALUED'
        ELSE 'OVERVALUED'
    END AS valuation_verdict,

    -- =========================================================================
    -- Supporting metrics for context
    -- =========================================================================
    sa.sector_avg_forward_pe,
    sa.sector_avg_trailing_pe,
    sa.stocks_in_sector,
    cf.trailing_pe,
    cf.forward_pe,
    cf.price_to_book,
    cf.peg_ratio,
    cf.trailing_eps,
    cf.forward_eps,
    cf.book_value,
    cf.earnings_growth,
    cf.revenue_growth,
    cf.return_on_equity,
    cf.profit_margin,
    cf.debt_to_equity,
    cf.beta,
    cf.dividend_yield,
    cf.fifty_two_week_high,
    cf.fifty_two_week_low,
    cf.fifty_day_avg,
    cf.two_hundred_day_avg

FROM current_fundamentals cf
LEFT JOIN sector_averages sa 
    ON cf.market = sa.market 
    AND cf.sector = sa.sector;
GO
