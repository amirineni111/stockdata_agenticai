USE stockdata_db;
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
        MONTH(calendar_date) AS cal_month,
        DATEPART(QUARTER, calendar_date) AS cal_quarter
    FROM dbo.market_calendar
    WHERE is_trading_day = 1
),
MonthBoundaries AS (
    SELECT
        t1.calendar_date,
        t1.market,
        -- Last trading day of the month: next trading day is a different month
        CASE WHEN t2.cal_month IS NOT NULL AND t1.cal_month <> t2.cal_month THEN 1 ELSE 0 END AS is_month_end,
        -- First trading day of the month: prev trading day is a different month
        CASE WHEN t0.cal_month IS NOT NULL AND t1.cal_month <> t0.cal_month THEN 1 ELSE 0 END AS is_month_start,
        -- Last trading day of the quarter
        CASE WHEN t1.cal_month IN (3,6,9,12)
             AND t2.cal_month IS NOT NULL AND t1.cal_month <> t2.cal_month THEN 1 ELSE 0 END AS is_quarter_end
    FROM TradingDaysOnly t1
    LEFT JOIN TradingDaysOnly t2
        ON t2.market = t1.market AND t2.td_seq = t1.td_seq + 1
    LEFT JOIN TradingDaysOnly t0
        ON t0.market = t1.market AND t0.td_seq = t1.td_seq - 1
),
HolidayDatesPerMarket AS (
    SELECT calendar_date, market
    FROM dbo.market_calendar
    WHERE is_holiday = 1
)
SELECT
    c.calendar_date,
    c.market,
    c.is_trading_day,
    c.is_holiday,
    c.holiday_name,
    c.day_of_week,
    c.is_options_expiry,

    -- Pre-holiday: trading day where the next calendar day is a holiday
    CASE WHEN c.is_trading_day = 1 AND c.next_day_is_holiday = 1 THEN 1 ELSE 0 END
        AS is_pre_holiday,

    -- Post-holiday: trading day where the previous calendar day was a holiday
    CASE WHEN c.is_trading_day = 1 AND c.prev_day_is_holiday = 1 THEN 1 ELSE 0 END
        AS is_post_holiday,

    -- Short week (fewer than 5 trading days)
    CASE WHEN tw.trading_days_in_week < 5 THEN 1 ELSE 0 END
        AS is_short_week,

    tw.trading_days_in_week,

    -- Month/Quarter boundaries
    ISNULL(mb.is_month_end, 0) AS is_month_end,
    ISNULL(mb.is_month_start, 0) AS is_month_start,
    ISNULL(mb.is_quarter_end, 0) AS is_quarter_end,

    -- Days until next holiday (capped at 999 if none found)
    ISNULL((
        SELECT MIN(DATEDIFF(day, c.calendar_date, h.calendar_date))
        FROM HolidayDatesPerMarket h
        WHERE h.market = c.market AND h.calendar_date > c.calendar_date
    ), 999) AS days_until_next_holiday,

    -- Days since last holiday
    ISNULL((
        SELECT MIN(DATEDIFF(day, h.calendar_date, c.calendar_date))
        FROM HolidayDatesPerMarket h
        WHERE h.market = c.market AND h.calendar_date < c.calendar_date
    ), 999) AS days_since_last_holiday,

    -- Other market closed on this date (cross-market mismatch)
    CASE
        WHEN c.market = 'NASDAQ' AND EXISTS (
            SELECT 1 FROM dbo.market_calendar o
            WHERE o.market = 'NSE' AND o.calendar_date = c.calendar_date
              AND o.is_trading_day = 0 AND o.is_holiday = 1
        ) THEN 1
        WHEN c.market = 'NSE' AND EXISTS (
            SELECT 1 FROM dbo.market_calendar o
            WHERE o.market = 'NASDAQ' AND o.calendar_date = c.calendar_date
              AND o.is_trading_day = 0 AND o.is_holiday = 1
        ) THEN 1
        ELSE 0
    END AS other_market_closed

FROM CalendarWithNav c
LEFT JOIN TradingWeeks tw
    ON tw.market = c.market
    AND tw.yr = DATEPART(YEAR, c.calendar_date)
    AND tw.wk = DATEPART(ISO_WEEK, c.calendar_date)
LEFT JOIN MonthBoundaries mb
    ON mb.market = c.market
    AND mb.calendar_date = c.calendar_date
WHERE c.is_trading_day = 1;
GO
