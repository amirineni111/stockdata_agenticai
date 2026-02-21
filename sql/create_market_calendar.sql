-- =============================================================================
-- Market Calendar Table + Derived Features View
-- =============================================================================
-- Creates a comprehensive trading calendar for NASDAQ, NSE, and FOREX markets.
-- Includes weekends, market holidays, options expiry days, and derived features
-- like is_pre_holiday, is_post_holiday, is_short_week for ML model consumption.
--
-- Usage:  Execute this entire script against stockdata_db
-- Author: Auto-generated for stockdata_agenticai platform
-- Date:   2026-02-21
-- =============================================================================

USE stockdata_db;
GO

-- =============================================================================
-- 1. CREATE TABLE
-- =============================================================================
IF OBJECT_ID('dbo.market_calendar', 'U') IS NOT NULL
    DROP TABLE dbo.market_calendar;
GO

CREATE TABLE dbo.market_calendar (
    calendar_date       DATE         NOT NULL,
    market              VARCHAR(20)  NOT NULL,   -- 'NASDAQ', 'NSE', 'FOREX'
    is_trading_day      BIT          NOT NULL DEFAULT 1,
    is_holiday          BIT          NOT NULL DEFAULT 0,
    holiday_name        VARCHAR(100) NULL,
    day_of_week         TINYINT      NOT NULL,   -- 0=Mon, 1=Tue, ..., 6=Sun (Python convention)
    is_options_expiry   BIT          NOT NULL DEFAULT 0,
    CONSTRAINT PK_market_calendar PRIMARY KEY (calendar_date, market)
);
GO

-- Index for fast date-range + market lookups
CREATE NONCLUSTERED INDEX IX_market_calendar_market_date
ON dbo.market_calendar (market, calendar_date)
INCLUDE (is_trading_day, is_holiday, holiday_name, is_options_expiry);
GO

-- =============================================================================
-- 2. POPULATE ALL DATES 2023-01-01 through 2026-12-31 (3 markets)
-- =============================================================================
-- Generate date spine using recursive CTE
;WITH DateSpine AS (
    SELECT CAST('2023-01-01' AS DATE) AS dt
    UNION ALL
    SELECT DATEADD(day, 1, dt) FROM DateSpine WHERE dt < '2026-12-31'
),
Markets AS (
    SELECT 'NASDAQ' AS market
    UNION ALL SELECT 'NSE'
    UNION ALL SELECT 'FOREX'
)
INSERT INTO dbo.market_calendar (calendar_date, market, is_trading_day, is_holiday, day_of_week)
SELECT
    d.dt,
    m.market,
    -- Default: weekdays are trading days (will override holidays below)
    CASE
        WHEN m.market = 'FOREX' THEN
            -- Forex: Mon-Fri trading (same weekday logic, bank holidays differ)
            CASE WHEN DATEPART(WEEKDAY, d.dt) IN (1, 7) THEN 0 ELSE 1 END  -- Sun=1, Sat=7
        ELSE
            -- Equity: Mon-Fri trading
            CASE WHEN DATEPART(WEEKDAY, d.dt) IN (1, 7) THEN 0 ELSE 1 END
    END,
    0,  -- is_holiday = 0 initially
    -- day_of_week: Python convention (0=Mon, 6=Sun)
    (DATEPART(WEEKDAY, d.dt) + 5) % 7
FROM DateSpine d
CROSS JOIN Markets m
OPTION (MAXRECURSION 1500);
GO

-- =============================================================================
-- 3. US MARKET HOLIDAYS (NASDAQ) — 2023-2026
-- =============================================================================

-- Helper: Update a holiday row
-- Sets is_holiday=1, is_trading_day=0, holiday_name for NASDAQ

-- 2023
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='New Year (Observed)' WHERE calendar_date='2023-01-02' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Martin Luther King Jr. Day' WHERE calendar_date='2023-01-16' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Presidents Day' WHERE calendar_date='2023-02-20' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Good Friday' WHERE calendar_date='2023-04-07' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Memorial Day' WHERE calendar_date='2023-05-29' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Juneteenth' WHERE calendar_date='2023-06-19' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Independence Day' WHERE calendar_date='2023-07-04' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Labor Day' WHERE calendar_date='2023-09-04' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Thanksgiving' WHERE calendar_date='2023-11-23' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Christmas' WHERE calendar_date='2023-12-25' AND market='NASDAQ';

-- 2024
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='New Year' WHERE calendar_date='2024-01-01' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Martin Luther King Jr. Day' WHERE calendar_date='2024-01-15' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Presidents Day' WHERE calendar_date='2024-02-19' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Good Friday' WHERE calendar_date='2024-03-29' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Memorial Day' WHERE calendar_date='2024-05-27' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Juneteenth' WHERE calendar_date='2024-06-19' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Independence Day' WHERE calendar_date='2024-07-04' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Labor Day' WHERE calendar_date='2024-09-02' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Thanksgiving' WHERE calendar_date='2024-11-28' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Christmas' WHERE calendar_date='2024-12-25' AND market='NASDAQ';

-- 2025
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='New Year' WHERE calendar_date='2025-01-01' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Martin Luther King Jr. Day' WHERE calendar_date='2025-01-20' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Presidents Day' WHERE calendar_date='2025-02-17' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Good Friday' WHERE calendar_date='2025-04-18' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Memorial Day' WHERE calendar_date='2025-05-26' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Juneteenth' WHERE calendar_date='2025-06-19' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Independence Day' WHERE calendar_date='2025-07-04' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Labor Day' WHERE calendar_date='2025-09-01' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Thanksgiving' WHERE calendar_date='2025-11-27' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Christmas' WHERE calendar_date='2025-12-25' AND market='NASDAQ';

-- 2026
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='New Year' WHERE calendar_date='2026-01-01' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Martin Luther King Jr. Day' WHERE calendar_date='2026-01-19' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Presidents Day' WHERE calendar_date='2026-02-16' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Good Friday' WHERE calendar_date='2026-04-03' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Memorial Day' WHERE calendar_date='2026-05-25' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Juneteenth' WHERE calendar_date='2026-06-19' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Independence Day (Observed)' WHERE calendar_date='2026-07-03' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Labor Day' WHERE calendar_date='2026-09-07' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Thanksgiving' WHERE calendar_date='2026-11-26' AND market='NASDAQ';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Christmas' WHERE calendar_date='2026-12-25' AND market='NASDAQ';
GO

-- =============================================================================
-- 4. NSE (INDIA) HOLIDAYS — 2023-2026
-- =============================================================================

-- 2023
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Republic Day' WHERE calendar_date='2023-01-26' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Holi' WHERE calendar_date='2023-03-07' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Ram Navami' WHERE calendar_date='2023-03-30' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Mahavir Jayanti' WHERE calendar_date='2023-04-04' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Good Friday' WHERE calendar_date='2023-04-07' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Dr. Ambedkar Jayanti' WHERE calendar_date='2023-04-14' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Maharashtra Day' WHERE calendar_date='2023-05-01' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Buddha Purnima' WHERE calendar_date='2023-05-05' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Eid ul-Adha (Bakri Id)' WHERE calendar_date='2023-06-29' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Independence Day' WHERE calendar_date='2023-08-15' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Ganesh Chaturthi' WHERE calendar_date='2023-09-19' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Mahatma Gandhi Jayanti' WHERE calendar_date='2023-10-02' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Dussehra' WHERE calendar_date='2023-10-24' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Diwali (Lakshmi Puja)' WHERE calendar_date='2023-11-14' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Guru Nanak Jayanti' WHERE calendar_date='2023-11-27' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Christmas' WHERE calendar_date='2023-12-25' AND market='NSE';

-- 2024
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Republic Day' WHERE calendar_date='2024-01-26' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Maha Shivaratri' WHERE calendar_date='2024-03-08' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Holi' WHERE calendar_date='2024-03-25' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Good Friday' WHERE calendar_date='2024-03-29' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Eid ul-Fitr' WHERE calendar_date='2024-04-11' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Ram Navami' WHERE calendar_date='2024-04-17' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Mahavir Jayanti' WHERE calendar_date='2024-04-21' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Maharashtra Day' WHERE calendar_date='2024-05-01' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Buddha Purnima' WHERE calendar_date='2024-05-23' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Eid ul-Adha (Bakri Id)' WHERE calendar_date='2024-06-17' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Muharram' WHERE calendar_date='2024-07-17' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Independence Day' WHERE calendar_date='2024-08-15' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Mahatma Gandhi Jayanti' WHERE calendar_date='2024-10-02' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Dussehra' WHERE calendar_date='2024-10-12' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Diwali (Lakshmi Puja)' WHERE calendar_date='2024-11-01' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Guru Nanak Jayanti' WHERE calendar_date='2024-11-15' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Christmas' WHERE calendar_date='2024-12-25' AND market='NSE';

-- 2025
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Republic Day' WHERE calendar_date='2025-01-26' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Maha Shivaratri' WHERE calendar_date='2025-02-26' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Holi' WHERE calendar_date='2025-03-14' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Id-ul-Fitr' WHERE calendar_date='2025-03-31' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Ram Navami' WHERE calendar_date='2025-04-06' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Dr. Ambedkar Jayanti' WHERE calendar_date='2025-04-14' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Good Friday' WHERE calendar_date='2025-04-18' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Maharashtra Day' WHERE calendar_date='2025-05-01' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Buddha Purnima' WHERE calendar_date='2025-05-12' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Eid ul-Adha (Bakri Id)' WHERE calendar_date='2025-06-07' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Independence Day' WHERE calendar_date='2025-08-15' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Ganesh Chaturthi' WHERE calendar_date='2025-08-27' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Mahatma Gandhi Jayanti' WHERE calendar_date='2025-10-02' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Dussehra' WHERE calendar_date='2025-10-02' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Diwali (Lakshmi Puja)' WHERE calendar_date='2025-10-20' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Guru Nanak Jayanti' WHERE calendar_date='2025-11-05' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Christmas' WHERE calendar_date='2025-12-25' AND market='NSE';

-- 2026
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Republic Day' WHERE calendar_date='2026-01-26' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Maha Shivaratri' WHERE calendar_date='2026-02-17' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Holi' WHERE calendar_date='2026-03-04' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Id-ul-Fitr' WHERE calendar_date='2026-03-21' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Ram Navami' WHERE calendar_date='2026-03-26' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Good Friday' WHERE calendar_date='2026-04-03' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Dr. Ambedkar Jayanti' WHERE calendar_date='2026-04-14' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Maharashtra Day' WHERE calendar_date='2026-05-01' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Buddha Purnima' WHERE calendar_date='2026-05-31' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Eid ul-Adha (Bakri Id)' WHERE calendar_date='2026-05-27' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Independence Day' WHERE calendar_date='2026-08-15' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Ganesh Chaturthi' WHERE calendar_date='2026-09-07' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Mahatma Gandhi Jayanti' WHERE calendar_date='2026-10-02' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Dussehra' WHERE calendar_date='2026-10-20' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Diwali (Lakshmi Puja)' WHERE calendar_date='2026-11-08' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Guru Nanak Jayanti' WHERE calendar_date='2026-11-24' AND market='NSE';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Christmas' WHERE calendar_date='2026-12-25' AND market='NSE';
GO

-- =============================================================================
-- 5. FOREX BANK HOLIDAYS (major liquidity-affecting holidays)
-- =============================================================================
-- Forex trades 24/5 but key bank holidays cause thin liquidity

-- US bank holidays (same as NASDAQ dates, affects USD pairs)
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='New Year (US)' WHERE calendar_date IN ('2023-01-02','2024-01-01','2025-01-01','2026-01-01') AND market='FOREX';
UPDATE dbo.market_calendar SET is_holiday=1, holiday_name='MLK Day (US - thin)' WHERE calendar_date IN ('2023-01-16','2024-01-15','2025-01-20','2026-01-19') AND market='FOREX';
UPDATE dbo.market_calendar SET is_holiday=1, holiday_name='Presidents Day (US - thin)' WHERE calendar_date IN ('2023-02-20','2024-02-19','2025-02-17','2026-02-16') AND market='FOREX';
UPDATE dbo.market_calendar SET is_holiday=1, holiday_name='Good Friday (US/UK)' WHERE calendar_date IN ('2023-04-07','2024-03-29','2025-04-18','2026-04-03') AND market='FOREX';
UPDATE dbo.market_calendar SET is_holiday=1, is_trading_day=0, holiday_name='Christmas' WHERE calendar_date IN ('2023-12-25','2024-12-25','2025-12-25','2026-12-25') AND market='FOREX';

-- UK bank holidays (affects GBP, EUR pairs)
UPDATE dbo.market_calendar SET is_holiday=1, holiday_name='UK Early May Bank Holiday' WHERE calendar_date IN ('2023-05-01','2024-05-06','2025-05-05','2026-05-04') AND market='FOREX';
UPDATE dbo.market_calendar SET is_holiday=1, holiday_name='UK Spring Bank Holiday' WHERE calendar_date IN ('2023-05-29','2024-05-27','2025-05-26','2026-05-25') AND market='FOREX';
UPDATE dbo.market_calendar SET is_holiday=1, holiday_name='UK Summer Bank Holiday' WHERE calendar_date IN ('2023-08-28','2024-08-26','2025-08-25','2026-08-31') AND market='FOREX';

-- Japan bank holidays (affects JPY pairs) - key ones only
UPDATE dbo.market_calendar SET is_holiday=1, holiday_name='Japan Golden Week' WHERE calendar_date IN ('2023-05-03','2023-05-04','2023-05-05','2024-05-03','2024-05-06','2025-05-03','2025-05-05','2025-05-06','2026-05-04','2026-05-05','2026-05-06') AND market='FOREX';
GO

-- =============================================================================
-- 6. US OPTIONS EXPIRY DAYS (3rd Friday of each month) — NASDAQ
-- =============================================================================
;WITH Months AS (
    SELECT CAST('2023-01-01' AS DATE) AS month_start
    UNION ALL
    SELECT DATEADD(month, 1, month_start) FROM Months WHERE month_start < '2026-12-01'
),
ThirdFridays AS (
    SELECT
        -- 3rd Friday = first Friday + 14 days
        DATEADD(day, 14 + ((6 - DATEPART(WEEKDAY, month_start) + 7) % 7), month_start) AS expiry_date
    FROM Months
)
UPDATE mc
SET mc.is_options_expiry = 1
FROM dbo.market_calendar mc
INNER JOIN ThirdFridays tf ON mc.calendar_date = tf.expiry_date
WHERE mc.market = 'NASDAQ'
OPTION (MAXRECURSION 100);
GO

-- =============================================================================
-- 7. NSE OPTIONS EXPIRY DAYS (last Thursday of each month)
-- =============================================================================
;WITH Months AS (
    SELECT CAST('2023-01-01' AS DATE) AS month_start
    UNION ALL
    SELECT DATEADD(month, 1, month_start) FROM Months WHERE month_start < '2026-12-01'
),
LastThursdays AS (
    SELECT
        -- Last day of month, then walk back to Thursday
        DATEADD(day,
            -((DATEPART(WEEKDAY, EOMONTH(month_start)) + 7 - 5) % 7),
            EOMONTH(month_start)
        ) AS expiry_date
    FROM Months
)
UPDATE mc
SET mc.is_options_expiry = 1
FROM dbo.market_calendar mc
INNER JOIN LastThursdays lt ON mc.calendar_date = lt.expiry_date
WHERE mc.market = 'NSE'
OPTION (MAXRECURSION 100);
GO

-- =============================================================================
-- 8. DERIVED FEATURES VIEW — vw_market_calendar_features
-- =============================================================================
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
        -- Next trading day's holiday status (for pre-holiday detection)
        LEAD(mc.is_holiday, 1) OVER (PARTITION BY mc.market ORDER BY mc.calendar_date) AS next_day_is_holiday,
        LEAD(mc.is_trading_day, 1) OVER (PARTITION BY mc.market ORDER BY mc.calendar_date) AS next_day_is_trading,
        -- Previous trading day's holiday status (for post-holiday detection)
        LAG(mc.is_holiday, 1) OVER (PARTITION BY mc.market ORDER BY mc.calendar_date) AS prev_day_is_holiday,
        LAG(mc.is_trading_day, 1) OVER (PARTITION BY mc.market ORDER BY mc.calendar_date) AS prev_day_is_trading
    FROM dbo.market_calendar mc
),
TradingWeeks AS (
    -- Count trading days per ISO week
    SELECT
        market,
        DATEPART(YEAR, calendar_date) AS yr,
        DATEPART(ISO_WEEK, calendar_date) AS wk,
        SUM(CAST(is_trading_day AS INT)) AS trading_days_in_week
    FROM dbo.market_calendar
    GROUP BY market, DATEPART(YEAR, calendar_date), DATEPART(ISO_WEEK, calendar_date)
),
HolidayDistances AS (
    -- Distance to nearest holiday (forward and backward)
    SELECT
        mc.calendar_date,
        mc.market,
        -- Days until next holiday
        (SELECT MIN(DATEDIFF(day, mc.calendar_date, h.calendar_date))
         FROM dbo.market_calendar h
         WHERE h.market = mc.market AND h.is_holiday = 1 AND h.calendar_date > mc.calendar_date
        ) AS days_until_next_holiday,
        -- Days since last holiday
        (SELECT MIN(DATEDIFF(day, h.calendar_date, mc.calendar_date))
         FROM dbo.market_calendar h
         WHERE h.market = mc.market AND h.is_holiday = 1 AND h.calendar_date < mc.calendar_date
        ) AS days_since_last_holiday
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

    -- Is this a trading day right before a holiday? (next non-weekend day is holiday)
    CASE WHEN c.is_trading_day = 1 AND c.next_day_is_holiday = 1 THEN 1 ELSE 0 END
        AS is_pre_holiday,

    -- Is this the first trading day after a holiday?
    CASE WHEN c.is_trading_day = 1 AND c.prev_day_is_holiday = 1 THEN 1 ELSE 0 END
        AS is_post_holiday,

    -- Short week indicator (fewer than 5 trading days due to holidays)
    CASE WHEN tw.trading_days_in_week < 5 THEN 1 ELSE 0 END
        AS is_short_week,

    tw.trading_days_in_week,

    -- Is this the last trading day of the month?
    CASE WHEN c.is_trading_day = 1
         AND LEAD(c.calendar_date, 1) OVER (PARTITION BY c.market ORDER BY c.calendar_date) IS NOT NULL
         AND MONTH(c.calendar_date) <> MONTH(LEAD(c.calendar_date, 1) OVER (PARTITION BY c.market ORDER BY c.calendar_date))
         THEN 1 ELSE 0 END
        AS is_month_end,

    -- Is this the first trading day of the month?
    CASE WHEN c.is_trading_day = 1
         AND LAG(c.calendar_date, 1) OVER (PARTITION BY c.market ORDER BY c.calendar_date) IS NOT NULL
         AND MONTH(c.calendar_date) <> MONTH(LAG(c.calendar_date, 1) OVER (PARTITION BY c.market ORDER BY c.calendar_date))
         THEN 1 ELSE 0 END
        AS is_month_start,

    -- Is this the last trading day of the quarter?
    CASE WHEN c.is_trading_day = 1
         AND MONTH(c.calendar_date) IN (3, 6, 9, 12)
         AND LEAD(c.calendar_date, 1) OVER (PARTITION BY c.market ORDER BY c.calendar_date) IS NOT NULL
         AND MONTH(c.calendar_date) <> MONTH(LEAD(c.calendar_date, 1) OVER (PARTITION BY c.market ORDER BY c.calendar_date))
         THEN 1 ELSE 0 END
        AS is_quarter_end,

    -- Distance features
    ISNULL(hd.days_until_next_holiday, 999) AS days_until_next_holiday,
    ISNULL(hd.days_since_last_holiday, 999) AS days_since_last_holiday,

    -- Other market closed (cross-market mismatch)
    CASE
        WHEN c.market = 'NASDAQ' AND EXISTS (
            SELECT 1 FROM dbo.market_calendar o
            WHERE o.market = 'NSE' AND o.calendar_date = c.calendar_date AND o.is_trading_day = 0 AND o.is_holiday = 1
        ) THEN 1
        WHEN c.market = 'NSE' AND EXISTS (
            SELECT 1 FROM dbo.market_calendar o
            WHERE o.market = 'NASDAQ' AND o.calendar_date = c.calendar_date AND o.is_trading_day = 0 AND o.is_holiday = 1
        ) THEN 1
        ELSE 0
    END AS other_market_closed

FROM CalendarWithNav c
LEFT JOIN TradingWeeks tw
    ON tw.market = c.market
    AND tw.yr = DATEPART(YEAR, c.calendar_date)
    AND tw.wk = DATEPART(ISO_WEEK, c.calendar_date)
LEFT JOIN HolidayDistances hd
    ON hd.market = c.market
    AND hd.calendar_date = c.calendar_date
WHERE c.is_trading_day = 1;
GO

-- =============================================================================
-- 9. VERIFICATION QUERIES
-- =============================================================================
-- Uncomment to verify after execution:
--
-- SELECT market, COUNT(*) total_days, SUM(CAST(is_trading_day AS INT)) trading_days,
--        SUM(CAST(is_holiday AS INT)) holidays, SUM(CAST(is_options_expiry AS INT)) expiry_days
-- FROM market_calendar GROUP BY market ORDER BY market;
--
-- SELECT TOP 20 * FROM vw_market_calendar_features WHERE market='NASDAQ' AND is_pre_holiday=1 ORDER BY calendar_date;
-- SELECT TOP 20 * FROM vw_market_calendar_features WHERE market='NSE' AND is_post_holiday=1 ORDER BY calendar_date;
-- SELECT TOP 20 * FROM vw_market_calendar_features WHERE market='NASDAQ' AND is_short_week=1 ORDER BY calendar_date;

PRINT 'market_calendar table created and populated successfully.';
PRINT 'vw_market_calendar_features view created successfully.';
GO
