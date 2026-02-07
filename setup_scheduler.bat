@echo off
REM ============================================================
REM Creates a Windows Task Scheduler task to run the daily
REM briefing every weekday (Mon-Fri) at 8:00 AM.
REM Run this script once as Administrator to set up the schedule.
REM ============================================================

echo Creating scheduled task: StockDataDailyBriefing
echo Schedule: Weekdays (Mon-Fri) at 8:00 AM
echo.

schtasks /create ^
    /tn "StockDataDailyBriefing" ^
    /tr "\"c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai\run_briefing.bat\"" ^
    /sc weekly ^
    /d MON,TUE,WED,THU,FRI ^
    /st 08:00 ^
    /rl HIGHEST ^
    /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Task created successfully!
    echo.
    echo To verify: schtasks /query /tn "StockDataDailyBriefing"
    echo To run now: schtasks /run /tn "StockDataDailyBriefing"
    echo To delete:  schtasks /delete /tn "StockDataDailyBriefing" /f
) else (
    echo.
    echo ERROR: Failed to create task. Try running as Administrator.
)

echo.
pause
