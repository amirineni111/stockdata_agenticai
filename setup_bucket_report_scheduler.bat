@echo off
REM ============================================================
REM Creates two Windows Task Scheduler tasks for the ML Bucket
REM Tracker emails, running Mon-Fri at 7:00 PM (after both the
REM NASDAQ and NSE market closes).
REM Run this script once as Administrator to set up the schedule.
REM ============================================================

echo Creating scheduled tasks: NasdaqBucketReport, NseBucketReport
echo Schedule: Weekdays (Mon-Fri) at 7:00 PM
echo.

schtasks /create ^
    /tn "NasdaqBucketReport" ^
    /tr "\"c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai\run_nasdaq_bucket_report.bat\"" ^
    /sc weekly ^
    /d MON,TUE,WED,THU,FRI ^
    /st 19:00 ^
    /rl HIGHEST ^
    /f

schtasks /create ^
    /tn "NseBucketReport" ^
    /tr "\"c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai\run_nse_bucket_report.bat\"" ^
    /sc weekly ^
    /d MON,TUE,WED,THU,FRI ^
    /st 19:00 ^
    /rl HIGHEST ^
    /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Tasks created successfully!
    echo.
    echo To verify:  schtasks /query /tn "NasdaqBucketReport"
    echo             schtasks /query /tn "NseBucketReport"
    echo To run now: schtasks /run /tn "NasdaqBucketReport"
    echo To delete:  schtasks /delete /tn "NasdaqBucketReport" /f
    echo             schtasks /delete /tn "NseBucketReport" /f
) else (
    echo.
    echo ERROR: Failed to create one or more tasks. Try running as Administrator.
)

echo.
pause
