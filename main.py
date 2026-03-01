"""
Stock Data Agentic AI Platform - Main Entry Point
==================================================
Runs the Daily Briefing Crew which orchestrates 8 specialist agents
to analyze market data, ML model performance, technical signals,
strategy opportunities, forex, risk, and fair value -- then compiles
and emails a comprehensive daily briefing.

Usage:
    python main.py                  # Run the full daily briefing
    python main.py --dry-run        # Run without sending email (print to console)
    python main.py --test-sql       # Test SQL Server connectivity only
    python main.py --test-email     # Test email sending only
    python main.py --preflight      # Run pre-flight checks only
    python main.py --status         # Show last 10 run results
    python main.py --status 20      # Show last 20 run results
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_sql_connection():
    """Test SQL Server connectivity and show available data."""
    print("=" * 60)
    print("TESTING SQL SERVER CONNECTION")
    print("=" * 60)

    try:
        import pyodbc
        from config.settings import get_sql_connection_string

        conn_str = get_sql_connection_string()
        print(f"Connection string: {conn_str[:50]}...")

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # List tables
        cursor.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
        )
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\nFound {len(tables)} tables:")
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM [{t}]")
            count = cursor.fetchone()[0]
            print(f"  - {t}: {count:,} rows")

        cursor.close()
        conn.close()
        print("\nSQL Server connection: OK")
        return True

    except Exception as e:
        print(f"\nSQL Server connection FAILED: {e}")
        return False


def test_email():
    """Send a test email to verify SMTP configuration."""
    print("=" * 60)
    print("TESTING EMAIL CONFIGURATION")
    print("=" * 60)

    try:
        from config.settings import (
            SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, EMAIL_FROM, EMAIL_TO
        )

        print(f"SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
        print(f"From: {EMAIL_FROM}")
        print(f"To: {EMAIL_TO}")

        if not SMTP_USERNAME:
            print("\nWARNING: SMTP_USERNAME not set in .env")
            return False

        from tools.email_tool import SendEmailTool
        tool = SendEmailTool()
        result = tool._run(
            subject="Test - Stock Data Agentic AI Platform",
            html_body=(
                "<html><body>"
                "<h2 style='color:#2c3e50;'>Test Email</h2>"
                "<p>This is a test email from the Stock Data Agentic AI Platform.</p>"
                "<p>If you received this, your email configuration is working correctly.</p>"
                f"<p><small>Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>"
                "</body></html>"
            ),
        )
        print(f"\nResult: {result}")
        return "successfully" in result.lower()

    except Exception as e:
        print(f"\nEmail test FAILED: {e}")
        return False


def run_daily_briefing(dry_run: bool = False):
    """Run the full daily briefing with rate-limit-safe execution."""
    print("=" * 60)
    print("STOCK DATA AGENTIC AI PLATFORM")
    print("Daily Briefing - Rate-Limit-Safe Execution")
    print(f"Date: {datetime.now().strftime('%B %d, %Y %H:%M:%S')}")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE] Email will not be sent.\n")

    try:
        from crews.daily_briefing_crew import run_daily_briefing_with_rate_limiting

        print("\nRunning 8 agents sequentially with 60s pauses between each")
        print("to respect Anthropic's 10k tokens/min rate limit.\n")
        print("Estimated total time: ~8-12 minutes")
        print("-" * 60)

        result = run_daily_briefing_with_rate_limiting()

        print("-" * 60)
        print("\nDAILY BRIEFING COMPLETE")
        print("=" * 60)
        print(f"\nFinal Output:\n{result}")

        return True

    except Exception as e:
        print(f"\nERROR: Crew execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_preflight_only():
    """Run only the pre-flight checks and report results."""
    from tools.preflight import run_preflight_checks
    can_proceed, results = run_preflight_checks(verbose=True)
    return can_proceed


def show_status(last_n: int = 10):
    """Show the run history status report."""
    from tools.run_tracker import print_status_report
    print_status_report(last_n=last_n)


def main():
    """Main entry point with CLI argument handling."""
    parser = argparse.ArgumentParser(
        description="Stock Data Agentic AI Platform - Daily Briefing"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the crew without sending email (output to console)",
    )
    parser.add_argument(
        "--test-sql",
        action="store_true",
        help="Test SQL Server connectivity only",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Test email sending only",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run pre-flight checks only (SQL, API key, data freshness, email)",
    )
    parser.add_argument(
        "--status",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="Show last N pipeline run results (default: 10)",
    )

    args = parser.parse_args()

    if args.test_sql:
        success = test_sql_connection()
        sys.exit(0 if success else 1)

    if args.test_email:
        success = test_email()
        sys.exit(0 if success else 1)

    if args.preflight:
        success = run_preflight_only()
        sys.exit(0 if success else 1)

    if args.status is not None:
        show_status(last_n=args.status)
        sys.exit(0)

    # Run the full daily briefing
    success = run_daily_briefing(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
