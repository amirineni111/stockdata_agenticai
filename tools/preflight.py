"""
Pre-flight validation checks for the Daily Briefing pipeline.
Runs before any agent to catch configuration, connectivity, and data
freshness issues early — avoiding wasted API tokens and time.
"""

import os
import sys
from datetime import datetime, timedelta

import pyodbc

from config.settings import (
    ANTHROPIC_API_KEY,
    LLM_MODEL,
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    EMAIL_FROM,
    EMAIL_TO,
    get_sql_connection_string,
    get_email_recipients,
)


class PreflightResult:
    """Structured result from a single pre-flight check."""

    def __init__(self, name: str, passed: bool, message: str, critical: bool = True):
        self.name = name
        self.passed = passed
        self.message = message
        self.critical = critical  # If True, pipeline should abort on failure

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        crit = " [CRITICAL]" if self.critical and not self.passed else ""
        return f"[{status}] {self.name}: {self.message}{crit}"


def check_api_key() -> PreflightResult:
    """Verify Anthropic API key is configured."""
    if not ANTHROPIC_API_KEY:
        return PreflightResult(
            "Anthropic API Key",
            False,
            "ANTHROPIC_API_KEY not set in .env",
            critical=True,
        )
    if len(ANTHROPIC_API_KEY) < 20:
        return PreflightResult(
            "Anthropic API Key",
            False,
            "ANTHROPIC_API_KEY appears too short — check .env",
            critical=True,
        )
    return PreflightResult(
        "Anthropic API Key",
        True,
        f"Set (model: {LLM_MODEL})",
    )


def check_sql_connection() -> PreflightResult:
    """Verify SQL Server is reachable."""
    try:
        conn_str = get_sql_connection_string()
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return PreflightResult("SQL Server", True, "Connected successfully")
    except pyodbc.Error as e:
        return PreflightResult(
            "SQL Server",
            False,
            f"Connection failed: {e}",
            critical=True,
        )
    except Exception as e:
        return PreflightResult(
            "SQL Server",
            False,
            f"Unexpected error: {e}",
            critical=True,
        )


def check_data_freshness(max_stale_days: int = 3) -> PreflightResult:
    """Check that market data is reasonably fresh (not older than max_stale_days).

    We allow up to 3 days to cover weekends (Friday data checked on Monday).
    """
    try:
        conn = pyodbc.connect(get_sql_connection_string(), timeout=10)
        cursor = conn.cursor()

        stale_tables = []
        tables = {
            "NASDAQ prices": "SELECT MAX(trading_date) FROM nasdaq_100_hist_data",
            "NSE prices": "SELECT MAX(trading_date) FROM nse_500_hist_data",
            "NASDAQ ML predictions": (
                "SELECT MAX(trading_date) FROM ml_trading_predictions"
            ),
            "NSE ML predictions": (
                "SELECT MAX(trading_date) FROM ml_nse_trading_predictions"
            ),
        }

        cutoff = datetime.now() - timedelta(days=max_stale_days)
        details = []

        for label, sql in tables.items():
            try:
                cursor.execute(sql)
                row = cursor.fetchone()
                if row and row[0]:
                    latest = row[0]
                    # Handle both date and datetime objects
                    if hasattr(latest, "date"):
                        latest_dt = datetime.combine(latest, datetime.min.time())
                    elif isinstance(latest, datetime):
                        latest_dt = latest
                    else:
                        latest_dt = datetime.strptime(str(latest)[:10], "%Y-%m-%d")

                    age_days = (datetime.now() - latest_dt).days
                    if latest_dt < cutoff:
                        stale_tables.append(f"{label} ({age_days}d old)")
                    details.append(f"{label}: {str(latest)[:10]} ({age_days}d)")
                else:
                    stale_tables.append(f"{label} (no data)")
            except Exception:
                # Table might not exist — non-critical
                details.append(f"{label}: table not found")

        cursor.close()
        conn.close()

        if stale_tables:
            return PreflightResult(
                "Data Freshness",
                False,
                f"Stale data: {', '.join(stale_tables)}. All: {'; '.join(details)}",
                critical=False,  # Warn but don't abort
            )
        return PreflightResult(
            "Data Freshness",
            True,
            f"All fresh: {'; '.join(details)}",
        )

    except Exception as e:
        return PreflightResult(
            "Data Freshness",
            False,
            f"Check failed: {e}",
            critical=False,
        )


def check_email_config() -> PreflightResult:
    """Verify email configuration is present (not connectivity — that's slow)."""
    missing = []
    if not SMTP_USERNAME:
        missing.append("SMTP_USERNAME")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if not EMAIL_FROM:
        missing.append("EMAIL_FROM")

    recipients = get_email_recipients("daily_briefing")
    if not recipients:
        missing.append("EMAIL_TO / email_recipients table")

    if missing:
        return PreflightResult(
            "Email Config",
            False,
            f"Missing: {', '.join(missing)}",
            critical=False,  # Can still run agents, just won't email
        )

    return PreflightResult(
        "Email Config",
        True,
        f"Configured — {len(recipients)} recipient(s): {', '.join(recipients)}",
    )


def check_template_exists() -> PreflightResult:
    """Verify the Jinja2 email template file is present."""
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "templates", "briefing_email.html"
    )
    if os.path.exists(template_path):
        return PreflightResult("Email Template", True, "briefing_email.html found")
    return PreflightResult(
        "Email Template",
        False,
        f"Missing: {template_path}",
        critical=True,
    )


def run_preflight_checks(verbose: bool = True) -> tuple[bool, list[PreflightResult]]:
    """Run all pre-flight checks and return (all_critical_passed, results).

    Returns:
        Tuple of (can_proceed: bool, results: list[PreflightResult])
        can_proceed is False only if a CRITICAL check failed.
    """
    checks = [
        check_api_key,
        check_sql_connection,
        check_data_freshness,
        check_email_config,
        check_template_exists,
    ]

    results = []
    for check_fn in checks:
        result = check_fn()
        results.append(result)

    critical_failures = [r for r in results if not r.passed and r.critical]
    warnings = [r for r in results if not r.passed and not r.critical]
    can_proceed = len(critical_failures) == 0

    if verbose:
        print("\n" + "=" * 60)
        print("PRE-FLIGHT CHECKS")
        print("=" * 60)
        for r in results:
            print(f"  {r}")
        if warnings:
            print(f"\n  Warnings: {len(warnings)} (non-blocking)")
        if critical_failures:
            print(f"\n  CRITICAL FAILURES: {len(critical_failures)} — pipeline ABORTED")
        else:
            print(f"\n  All critical checks passed — pipeline clear to run")
        print("=" * 60)

    return can_proceed, results
