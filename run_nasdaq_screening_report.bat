@echo off
REM ============================================================
REM NASDAQ Weekly Stock Screening Report - Excel-attachment email
REM runner. Exports the latest snapshot of 7 fundamental screening
REM views (growth, GARP, value, quality, fundamental scoring,
REM fair value, dividend) plus week-over-week Top 10 Gain/Loss
REM workbooks (14 files total) and emails them as attachments.
REM Schedule via Windows Task Scheduler to run weekly (e.g. Monday
REM morning, after the weekend's fundamentals refresh).
REM ============================================================

cd /d "c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai"

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%i"
set "RUN_LOG=logs\screening_nasdaq_%RUN_TS%.log"
py -3.12 weekly_screening_report.py --market nasdaq > "%RUN_LOG%" 2>&1

echo [NASDAQ screening] Exit code: %ERRORLEVEL% >> logs\run_log.txt
echo [NASDAQ screening] Ran at: %DATE% %TIME% >> logs\run_log.txt
echo [NASDAQ screening] Log file: %RUN_LOG% >> logs\run_log.txt

REM pause
