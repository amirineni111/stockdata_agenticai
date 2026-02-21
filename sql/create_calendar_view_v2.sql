USE stockdata_db;
GO

IF OBJECT_ID('dbo.vw_market_calendar_features', 'V') IS NOT NULL
    DROP VIEW dbo.vw_market_calendar_features;
GO

CREATE VIEW dbo.vw_market_calendar_features AS
WITH CalendarWithNav AS (
    SELECT
        mc.calendar_date,
        mc.market,
        mc.is_trading_day,
        mc.is_holiday,
        mc.holiday_name,
        mc.day_of_week,
        mc.is_options_expiry,
        LEAD(mc.is_holiday, 1) OVER (PARTITION BY mc.market ORDER BY mc.calendar_date) AS next_day_is_holiday,
        LAG(mc.is_holiday, 1) OVER (PARTITION BY mc.market ORDER BY mc.calendar_date) AS prev_day_is_holiday
    FROM dbo.market_calendar mc
),
TradingWeeks AS (
    SELECT
        market,
        DATEPART(YEAR, calendar_date) AS yr,
        DATEPART(ISO_WEEK, calendar_date) AS wk,
        SUM(CAST(is_trading_day AS INT)) AS trading_days_in_week
    FROM dbo.market_calendar
    GROUP BY market, DATEPART(YEAR, calendar_date), DATEPART(ISO_WEEK, calendar_date)
),
TradingDaysOnly AS (
    SELECT
        calendar_date,
        market,
        ROW_NUMBER() OVER (PARTITION BY market ORDER BY calendar_date) AS td_seq,
        MONTH(calendar_date) AS cal_month
    FROM dbo.market_calendar
    WHERE is_trading_day = 1
),
MonthBoundaries AS (
    SELECT
        t1.calendar_date,
        t1.market,
        CASE WHEN t2.cal_month IS NOT NULL AND t1.cal_month <> t2.cal_month THEN 1 ELSE 0 END AS is_month_end,
        CASE WHEN t0.cal_month IS NOT NULL AND t1.cal_month <> t0.cal_month THEN 1 ELSE 0 END AS is_month_start,
        CASE WHEN t1.cal_month IN (3,6,9,12)
             AND t2.cal_month IS NOT NULL AND t1.cal_month <> t2.cal_month THEN 1 ELSE 0 END AS is_quarter_end
    FROM TradingDaysOnly t1
    LEFT JOIN TradingDaysOnly t2
        ON t2.market = t1.market AND t2.td_seq = t1.td_seq + 1
    LEFT JOIN TradingDaysOnly t0
        ON t0.market = t1.market AND t0.td_seq = t1.td_seq - 1
),
-- Pre-compute next/prev holiday dates per market using CROSS APPLY equivalent
HolidayDistances AS (
    SELECT
        td.calendar_date,
        td.market,
        next_h.next_holiday_date,
        prev_h.prev_holiday_date
    FROM (
        SELECT DISTINCT calendar_date, market FROM dbo.market_calendar WHERE is_trading_day = 1
    ) td
    OUTER APPLY (
        SELECT TOP 1 h.calendar_date AS next_holiday_date
        FROM dbo.market_calendar h
        WHERE h.market = td.market AND h.is_holiday = 1 AND h.calendar_date > td.calendar_date
        ORDER BY h.calendar_date ASC
    ) next_h
    OUTER APPLY (
        SELECT TOP 1 h.calendar_date AS prev_holiday_date
        FROM dbo.market_calendar h
        WHERE h.market = td.market AND h.is_holiday = 1 AND h.calendar_date < td.calendar_date
        ORDER BY h.calendar_date DESC
    ) prev_h
),
-- Cross-market holiday check
CrossMarket AS (
    SELECT
        mc.calendar_date,
        mc.market,
        CASE
            WHEN mc.market = 'NASDAQ' AND EXISTS (
                SELECT 1 FROM dbo.market_calendar o
                WHERE o.market = 'NSE' AND o.calendar_date = mc.calendar_date
                  AND o.is_trading_day = 0 AND o.is_holiday = 1
            ) THEN 1
            WHEN mc.market = 'NSE' AND EXISTS (
                SELECT 1 FROM dbo.market_calendar o
                WHERE o.market = 'NASDAQ' AND o.calendar_date = mc.calendar_date
                  AND o.is_trading_day = 0 AND o.is_holiday = 1
            ) THEN 1
            ELSE 0
        END AS other_market_closed
    FROM dbo.market_calendar mc
    WHERE mc.is_trading_day = 1
)
SELECT
    c.calendar_date,
    c.market,
    c.is_trading_day,
    c.is_holiday,
    c.holiday_name,
    c.day_of_week,
    c.is_options_expiry,

    CASE WHEN c.is_trading_day = 1 AND c.next_day_is_holiday = 1 THEN 1 ELSE 0 END
        AS is_pre_holiday,

    CASE WHEN c.is_trading_day = 1 AND c.prev_day_is_holiday = 1 THEN 1 ELSE 0 END
        AS is_post_holiday,

    CASE WHEN tw.trading_days_in_week < 5 THEN 1 ELSE 0 END
        AS is_short_week,

    tw.trading_days_in_week,

    ISNULL(mb.is_month_end, 0) AS is_month_end,
    ISNULL(mb.is_month_start, 0) AS is_month_start,
    ISNULL(mb.is_quarter_end, 0) AS is_quarter_end,

    ISNULL(DATEDIFF(day, c.calendar_date, hd.next_holiday_date), 999) AS days_until_next_holiday,
    ISNULL(DATEDIFF(day, hd.prev_holiday_date, c.calendar_date), 999) AS days_since_last_holiday,

    ISNULL(cm.other_market_closed, 0) AS other_market_closed

FROM CalendarWithNav c
LEFT JOIN TradingWeeks tw
    ON tw.market = c.market
    AND tw.yr = DATEPART(YEAR, c.calendar_date)
    AND tw.wk = DATEPART(ISO_WEEK, c.calendar_date)
LEFT JOIN MonthBoundaries mb
    ON mb.market = c.market
    AND mb.calendar_date = c.calendar_date
LEFT JOIN HolidayDistances hd
    ON hd.market = c.market
    AND hd.calendar_date = c.calendar_date
LEFT JOIN CrossMarket cm
    ON cm.market = c.market
    AND cm.calendar_date = c.calendar_date
WHERE c.is_trading_day = 1;
GO
