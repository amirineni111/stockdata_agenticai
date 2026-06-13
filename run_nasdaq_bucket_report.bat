@echo off
REM ============================================================
REM NASDAQ ML Bucket Tracker - daily HTML email runner.
REM Schedule via Windows Task Scheduler to run Mon-Fri after
REM the US market close (~7 PM EST).
REM ============================================================

cd /d "c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai"

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%i"
set "RUN_LOG=logs\bucket_nasdaq_%RUN_TS%.log"
py -3.12 ml_bucket_report.py --market nasdaq > "%RUN_LOG%" 2>&1

echo [NASDAQ bucket] Exit code: %ERRORLEVEL% >> logs\run_log.txt
echo [NASDAQ bucket] Ran at: %DATE% %TIME% >> logs\run_log.txt
echo [NASDAQ bucket] Log file: %RUN_LOG% >> logs\run_log.txt

REM pause
