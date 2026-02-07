@echo off
REM ============================================================
REM Stock Data Agentic AI - Daily Briefing Runner
REM Schedule this script via Windows Task Scheduler to run
REM every weekday morning before market opens.
REM ============================================================

REM Set the project directory
cd /d "c:\Users\sreea\OneDrive\Desktop\stockdata_agenticai"

REM Activate virtual environment if using one
REM call venv\Scripts\activate.bat

REM Run the daily briefing
python main.py

REM Log the exit code
echo Exit code: %ERRORLEVEL% >> logs\run_log.txt
echo Ran at: %DATE% %TIME% >> logs\run_log.txt

REM Pause if running manually (comment out for scheduled runs)
REM pause
