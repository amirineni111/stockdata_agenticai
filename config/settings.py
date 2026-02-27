"""
Central configuration for the Stock Data Agentic AI platform.
Loads settings from .env file and provides typed access.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# =============================================================================
# Anthropic Claude Configuration
# =============================================================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

# =============================================================================
# SQL Server Configuration
# =============================================================================
SQL_SERVER = os.getenv("SQL_SERVER", "localhost")
SQL_DATABASE = os.getenv("SQL_DATABASE", "")
SQL_DRIVER = os.getenv("SQL_DRIVER", "{ODBC Driver 17 for SQL Server}")
SQL_USERNAME = os.getenv("SQL_USERNAME", "")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")
SQL_TRUSTED_CONNECTION = os.getenv("SQL_TRUSTED_CONNECTION", "yes")


def get_sql_connection_string() -> str:
    """Build the pyodbc connection string based on environment config."""
    if SQL_TRUSTED_CONNECTION.lower() == "yes":
        return (
            f"DRIVER={SQL_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
    else:
        return (
            f"DRIVER={SQL_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD};"
            f"TrustServerCertificate=yes;"
        )


# =============================================================================
# Email Configuration (Office 365)
# =============================================================================
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

def get_email_recipients(briefing_type: str = "daily_briefing") -> list[str]:
    """Fetch active email recipients from the database.
    
    Falls back to EMAIL_TO from .env if the database table doesn't exist
    or the query fails.
    
    Args:
        briefing_type: Filter recipients by briefing type (default: 'daily_briefing').
    
    Returns:
        List of email addresses.
    """
    try:
        import pyodbc
        conn = pyodbc.connect(get_sql_connection_string())
        cursor = conn.cursor()
        cursor.execute(
            "SELECT email_address FROM email_recipients "
            "WHERE is_active = 1 AND briefing_type = ? "
            "ORDER BY recipient_type, id",
            briefing_type,
        )
        recipients = [row.email_address.strip() for row in cursor.fetchall()]
        conn.close()
        if recipients:
            return recipients
    except Exception:
        pass  # Fall through to .env fallback

    # Fallback to .env EMAIL_TO
    if EMAIL_TO:
        return [addr.strip() for addr in EMAIL_TO.split(",") if addr.strip()]
    return []


# =============================================================================
# Agent Configuration
# =============================================================================
AGENT_MAX_ITER = int(os.getenv("AGENT_MAX_ITER", "5"))
AGENT_VERBOSE = os.getenv("AGENT_VERBOSE", "true").lower() == "true"
AGENT_MAX_RPM = int(os.getenv("AGENT_MAX_RPM", "4"))
