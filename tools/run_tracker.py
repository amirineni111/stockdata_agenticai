"""
Structured logging for the Daily Briefing pipeline.
Provides per-agent timing, success/failure tracking, and a persistent
JSON run history for post-mortem analysis and the --status CLI flag.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Module-level logger setup
# ---------------------------------------------------------------------------

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

# JSON run-history file (appended after each run)
RUN_HISTORY_FILE = os.path.join(_LOG_DIR, "run_history.json")


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root pipeline logger.

    Logs to both console (INFO+) and a timestamped file (DEBUG+).
    """
    logger = logging.getLogger("stockdata_agenticai")
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler — one per day
    today_str = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(_LOG_DIR, f"briefing_{today_str}.log")
    file_h = logging.FileHandler(log_file, encoding="utf-8")
    file_h.setLevel(logging.DEBUG)
    file_h.setFormatter(formatter)
    logger.addHandler(file_h)

    return logger


# ---------------------------------------------------------------------------
# Run record dataclass (dict-based for JSON serialization)
# ---------------------------------------------------------------------------

def _new_run_record() -> dict:
    """Create a blank run record."""
    return {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "total_duration_sec": None,
        "status": "running",  # running | success | partial | failed
        "agents_total": 8,
        "agents_succeeded": 0,
        "agents_failed": 0,
        "email_sent": False,
        "email_recipients": None,
        "preflight_passed": None,
        "preflight_warnings": [],
        "agent_details": {},
        "error": None,
    }


def _new_agent_record(agent_name: str) -> dict:
    return {
        "agent_name": agent_name,
        "status": "pending",  # pending | running | success | failed | skipped
        "started_at": None,
        "finished_at": None,
        "duration_sec": None,
        "retries": 0,
        "output_length": 0,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Persistent run history
# ---------------------------------------------------------------------------

def save_run_record(record: dict) -> None:
    """Append a run record to the JSON run-history file."""
    history = load_run_history()
    history.append(record)

    # Keep last 100 runs to avoid unbounded growth
    if len(history) > 100:
        history = history[-100:]

    with open(RUN_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)


def load_run_history() -> list[dict]:
    """Load run history from disk."""
    if not os.path.exists(RUN_HISTORY_FILE):
        return []
    try:
        with open(RUN_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def print_status_report(last_n: int = 10) -> None:
    """Print a human-readable status report of last N runs."""
    history = load_run_history()
    if not history:
        print("No run history found.")
        return

    runs = history[-last_n:]
    print("\n" + "=" * 80)
    print(f"PIPELINE STATUS — Last {len(runs)} Run(s)")
    print("=" * 80)

    for run in runs:
        started = run.get("started_at", "?")[:19]
        status = run.get("status", "?").upper()
        duration = run.get("total_duration_sec")
        dur_str = f"{duration:.0f}s" if duration else "?"
        agents_ok = run.get("agents_succeeded", 0)
        agents_fail = run.get("agents_failed", 0)
        email = "Yes" if run.get("email_sent") else "No"

        status_icon = {"SUCCESS": "+", "PARTIAL": "~", "FAILED": "X", "RUNNING": ">"}.get(status, "?")

        print(f"\n  [{status_icon}] {started}  Status: {status}  Duration: {dur_str}")
        print(f"      Agents: {agents_ok}/8 succeeded, {agents_fail} failed  |  Email sent: {email}")

        # Show per-agent details if any failed
        agent_details = run.get("agent_details", {})
        failed_agents = {k: v for k, v in agent_details.items() if v.get("status") == "failed"}
        if failed_agents:
            for name, detail in failed_agents.items():
                err = detail.get("error", "Unknown error")[:80]
                retries = detail.get("retries", 0)
                print(f"      FAILED: {name} (retries: {retries}) — {err}")

        # Show preflight warnings
        warnings = run.get("preflight_warnings", [])
        if warnings:
            for w in warnings:
                print(f"      WARNING: {w}")

    # Summary
    total = len(history)
    successes = sum(1 for r in history if r.get("status") == "success")
    partials = sum(1 for r in history if r.get("status") == "partial")
    failures = sum(1 for r in history if r.get("status") == "failed")
    rate = (successes / total * 100) if total else 0

    print(f"\n  --- All-Time ({total} runs) ---")
    print(f"  Success: {successes} ({rate:.0f}%)  |  Partial: {partials}  |  Failed: {failures}")
    print("=" * 80)
