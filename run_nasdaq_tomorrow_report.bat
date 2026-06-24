@echo off
REM ============================================================
REM NASDAQ ML Tomorrow Predictions - forward-looking HTML email
REM runner. Reports the latest ML signals (S1 and S1^S2) by price
REM bucket as an outlook for the next trading day. Schedule via
REM Windows Task Scheduler to run Mon-Fri after the US market
REM close (~7 PM EST, alongside the bucket back-tracking reports).
REM ============================================================

cd /d "c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai"

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%i"
set "RUN_LOG=logs\tomorrow_nasdaq_%RUN_TS%.log"
py -3.12 ml_tomorrow_report.py --market nasdaq > "%RUN_LOG%" 2>&1

echo [NASDAQ tomorrow] Exit code: %ERRORLEVEL% >> logs\run_log.txt
echo [NASDAQ tomorrow] Ran at: %DATE% %TIME% >> logs\run_log.txt
echo [NASDAQ tomorrow] Log file: %RUN_LOG% >> logs\run_log.txt

REM pause
