@echo off
REM ============================================================
REM Optional convenience: creates two Windows Task Scheduler tasks
REM for the Weekly Stock Screening Report emails (NASDAQ + NSE),
REM running once a week on Monday at 6:00 AM. Adjust /d and /st
REM below if you want a different day/time, then run this script
REM once as Administrator. You can also skip this and point Task
REM Scheduler at run_nasdaq_screening_report.bat /
REM run_nse_screening_report.bat yourself.
REM ============================================================

echo Creating scheduled tasks: NasdaqScreeningReport, NseScreeningReport
echo Schedule: Weekly on Monday at 6:00 AM
echo.

schtasks /create ^
    /tn "NasdaqScreeningReport" ^
    /tr "\"c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai\run_nasdaq_screening_report.bat\"" ^
    /sc weekly ^
    /d MON ^
    /st 06:00 ^
    /rl HIGHEST ^
    /f

schtasks /create ^
    /tn "NseScreeningReport" ^
    /tr "\"c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai\run_nse_screening_report.bat\"" ^
    /sc weekly ^
    /d MON ^
    /st 06:15 ^
    /rl HIGHEST ^
    /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Tasks created successfully!
    echo.
    echo To verify:  schtasks /query /tn "NasdaqScreeningReport"
    echo             schtasks /query /tn "NseScreeningReport"
    echo To run now: schtasks /run /tn "NasdaqScreeningReport"
    echo To delete:  schtasks /delete /tn "NasdaqScreeningReport" /f
    echo             schtasks /delete /tn "NseScreeningReport" /f
) else (
    echo.
    echo ERROR: Failed to create one or more tasks. Try running as Administrator.
)

echo.
pause
