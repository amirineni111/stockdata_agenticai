@echo off
REM ============================================================
REM Forex ML Bucket Tracker - daily HTML email runner.
REM Schedule via Windows Task Scheduler to run Mon-Fri at
REM ~7 PM EST (alongside the NASDAQ/NSE bucket reports).
REM ============================================================

cd /d "c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai"

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%i"
set "RUN_LOG=logs\bucket_forex_%RUN_TS%.log"
py -3.12 forex_bucket_report.py > "%RUN_LOG%" 2>&1

echo [Forex bucket] Exit code: %ERRORLEVEL% >> logs\run_log.txt
echo [Forex bucket] Ran at: %DATE% %TIME% >> logs\run_log.txt
echo [Forex bucket] Log file: %RUN_LOG% >> logs\run_log.txt

REM pause
