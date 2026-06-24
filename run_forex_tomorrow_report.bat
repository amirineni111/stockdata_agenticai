@echo off
REM ============================================================
REM Forex ML Tomorrow Predictions - forward-looking HTML email
REM runner. Reports the latest Forex ML signals (S1 only) grouped
REM by direction as an outlook for the next trading day. Schedule
REM via Windows Task Scheduler to run Mon-Fri at ~7 PM EST
REM (alongside the bucket back-tracking reports).
REM ============================================================

cd /d "c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai"

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%i"
set "RUN_LOG=logs\tomorrow_forex_%RUN_TS%.log"
py -3.12 forex_tomorrow_report.py > "%RUN_LOG%" 2>&1

echo [Forex tomorrow] Exit code: %ERRORLEVEL% >> logs\run_log.txt
echo [Forex tomorrow] Ran at: %DATE% %TIME% >> logs\run_log.txt
echo [Forex tomorrow] Log file: %RUN_LOG% >> logs\run_log.txt

REM pause
