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

# Active model for every CrewAI agent + the chat assistant. Swap this one value
# in .env to move the whole platform between models — the agents adapt their
# request parameters automatically via the profile helpers below.
#   claude-sonnet-4-6  — cheap workhorse, accepts temperature, no thinking
#   claude-fable-5     — most capable, rejects temperature, thinking always on
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")

# Convenience aliases so callers/scripts can name a model without hardcoding it.
LLM_MODEL_SONNET = os.getenv("LLM_MODEL_SONNET", "claude-sonnet-4-6")
LLM_MODEL_FABLE = os.getenv("LLM_MODEL_FABLE", "claude-fable-5")

# --- Model capability profiles -----------------------------------------------
# Newer Claude models removed the sampling parameters and made extended thinking
# mandatory. Sending `temperature` to one of these returns HTTP 400, and because
# thinking output counts against max_tokens, a budget sized for a non-thinking
# model truncates the answer mid-sentence. These prefix lists let one code path
# serve both generations.

# `temperature` / `top_p` / `top_k` are rejected (400) by these model families.
_MODELS_REJECTING_TEMPERATURE = (
    "claude-fable-",
    "claude-mythos-",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-sonnet-5",
)

# Thinking is always on and cannot be disabled — max_tokens covers thinking
# tokens PLUS the visible answer, so these models need a much larger budget.
_MODELS_ALWAYS_THINKING = (
    "claude-fable-",
    "claude-mythos-",
    "claude-opus-5",
)

# Floor applied to max_tokens on always-thinking models so the visible answer
# still has room after the model has finished reasoning.
LLM_THINKING_MIN_MAX_TOKENS = int(os.getenv("LLM_THINKING_MIN_MAX_TOKENS", "8000"))


def model_rejects_temperature(model: str | None = None) -> bool:
    """True if passing `temperature` to this model would return HTTP 400."""
    return (model or LLM_MODEL).startswith(_MODELS_REJECTING_TEMPERATURE)


def model_always_thinks(model: str | None = None) -> bool:
    """True if this model always emits thinking tokens (billed against max_tokens)."""
    return (model or LLM_MODEL).startswith(_MODELS_ALWAYS_THINKING)


def resolve_max_tokens(requested: int, model: str | None = None) -> int:
    """Raise an agent's token budget to the thinking floor when the model needs it.

    Agents pick budgets (1500-2000) sized for a non-thinking model. On an
    always-thinking model those budgets are consumed by reasoning before any
    answer is produced, so lift them to LLM_THINKING_MIN_MAX_TOKENS.
    """
    if model_always_thinks(model):
        return max(requested, LLM_THINKING_MIN_MAX_TOKENS)
    return requested

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

def get_email_recipients_by_type(briefing_type: str = "daily_briefing") -> dict[str, list[str]]:
    """Fetch active email recipients from the database, grouped by recipient_type.

    Falls back to EMAIL_TO from .env (as BCC) if the database table doesn't
    exist or the query fails.

    Args:
        briefing_type: Filter recipients by briefing type (default: 'daily_briefing').

    Returns:
        Dict with keys 'TO', 'CC', 'BCC' mapping to lists of email addresses.
    """
    result: dict[str, list[str]] = {"TO": [], "CC": [], "BCC": []}
    try:
        import pyodbc
        conn = pyodbc.connect(get_sql_connection_string())
        cursor = conn.cursor()
        cursor.execute(
            "SELECT email_address, recipient_type FROM email_recipients "
            "WHERE is_active = 1 AND briefing_type = ? "
            "ORDER BY recipient_type, id",
            briefing_type,
        )
        for row in cursor.fetchall():
            rtype = (row.recipient_type or "BCC").strip().upper()
            if rtype not in result:
                rtype = "BCC"
            result[rtype].append(row.email_address.strip())
        conn.close()
        if any(result.values()):
            return result
    except Exception:
        pass  # Fall through to .env fallback

    # Fallback to .env EMAIL_TO (default to BCC)
    if EMAIL_TO:
        result["BCC"] = [addr.strip() for addr in EMAIL_TO.split(",") if addr.strip()]
    return result


def get_email_recipients(briefing_type: str = "daily_briefing") -> list[str]:
    """Fetch all active email recipients as a flat list (for logging/backward compat)."""
    by_type = get_email_recipients_by_type(briefing_type)
    return by_type["TO"] + by_type["CC"] + by_type["BCC"]


# =============================================================================
# Agent Configuration
# =============================================================================
AGENT_MAX_ITER = int(os.getenv("AGENT_MAX_ITER", "5"))
AGENT_VERBOSE = os.getenv("AGENT_VERBOSE", "true").lower() == "true"
AGENT_MAX_RPM = int(os.getenv("AGENT_MAX_RPM", "4"))
