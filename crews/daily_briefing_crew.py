"""
Daily Briefing Crew - Master Orchestrator
Assembles all specialist agents into a CrewAI pipeline.

Architecture:
  Runs each agent independently with rate-limit-safe delays,
  then compiles all findings via Jinja2 template and sends email.

Stability features:
  - Per-agent try/except with configurable retry (default: 2 attempts)
  - Graceful degradation: failed agents show "Analysis unavailable"
  - Structured logging with per-agent timing
  - Output validation (detects error strings, empty results)
  - Pre-flight checks run before any agent
"""

import time
import os
import re
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from crewai import Crew, Task, Process
from datetime import date, datetime
from jinja2 import Environment, FileSystemLoader

from agents.market_intel_agent import create_market_intel_agent
from agents.ml_analyst_agent import create_ml_analyst_agent
from agents.tech_signal_agent import create_tech_signal_agent
from agents.strategy_trade_agent import create_strategy_trade_agent
from agents.forex_agent import create_forex_agent
from agents.risk_agent import create_risk_agent
from agents.cross_strategy_agent import create_cross_strategy_agent

from config.settings import (
    SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
    EMAIL_FROM, EMAIL_FROM_NAME, EMAIL_TO,
    get_email_recipients, get_email_recipients_by_type,
)

from tools.run_tracker import (
    setup_logging,
    _new_run_record,
    _new_agent_record,
    save_run_record,
)
from tools.preflight import run_preflight_checks

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_AGENT_RETRIES = 2          # Total attempts per agent (1 = no retry)
PAUSE_SECONDS = 60             # Pause between agents for rate-limit
RETRY_PAUSE_SECONDS = 60       # Extra pause before a retry attempt (must exceed rate-limit window)

# Error patterns that indicate the agent output is garbage
_ERROR_PATTERNS = [
    "i encountered an error",
    "i apologize",
    "unable to execute",
    "sql error:",
    "error executing query",
    "connection failed",
    "rate limit",
    "max iterations reached",
    "agent stopped due to iteration limit",
]

logger = setup_logging()


def _run_single_agent(agent, task_description: str, expected_output: str) -> str:
    """Run a single agent as its own mini-crew and return the result."""
    task = Task(
        description=task_description,
        expected_output=expected_output,
        agent=agent,
    )

    mini_crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
        memory=False,
    )

    result = mini_crew.kickoff()
    return result.raw if hasattr(result, "raw") else str(result)


def _validate_agent_output(output: str, agent_name: str) -> tuple[bool, str]:
    """Validate that agent output is usable.

    Returns:
        (is_valid, reason) — reason is empty string when valid.
    """
    if not output or not output.strip():
        return False, "Empty output"

    if len(output.strip()) < 30:
        return False, f"Output too short ({len(output.strip())} chars)"

    lowered = output.lower()
    for pattern in _ERROR_PATTERNS:
        if pattern in lowered:
            return False, f"Error pattern detected: '{pattern}'"

    return True, ""


def _run_agent_with_retry(
    agent_name: str,
    create_fn,
    task_description: str,
    expected_output: str,
    agent_record: dict,
) -> str:
    """Run an agent with retry logic and output validation.

    Returns the agent output string, or a fallback message on failure.
    """
    last_error = None

    for attempt in range(1, MAX_AGENT_RETRIES + 1):
        agent_record["status"] = "running"
        agent_record["started_at"] = datetime.now().isoformat()

        try:
            if attempt > 1:
                logger.info(
                    f"  [{agent_name}] Retry attempt {attempt}/{MAX_AGENT_RETRIES} "
                    f"(waiting {RETRY_PAUSE_SECONDS}s)..."
                )
                time.sleep(RETRY_PAUSE_SECONDS)

            agent = create_fn()
            output = _run_single_agent(agent, task_description, expected_output)

            # Validate output quality
            is_valid, reason = _validate_agent_output(output, agent_name)
            if not is_valid:
                last_error = f"Output validation failed: {reason}"
                logger.warning(f"  [{agent_name}] {last_error}")
                agent_record["retries"] = attempt
                continue  # retry

            # Success
            agent_record["status"] = "success"
            agent_record["finished_at"] = datetime.now().isoformat()
            started = datetime.fromisoformat(agent_record["started_at"])
            agent_record["duration_sec"] = round(
                (datetime.now() - started).total_seconds(), 1
            )
            agent_record["output_length"] = len(output)
            agent_record["retries"] = attempt - 1
            logger.info(
                f"  [{agent_name}] Completed in {agent_record['duration_sec']}s "
                f"({agent_record['output_length']} chars, "
                f"{agent_record['retries']} retries)"
            )
            return output

        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)}"
            logger.error(f"  [{agent_name}] Attempt {attempt} failed: {last_error}")
            logger.debug(traceback.format_exc())
            agent_record["retries"] = attempt

    # All attempts exhausted
    agent_record["status"] = "failed"
    agent_record["finished_at"] = datetime.now().isoformat()
    agent_record["error"] = last_error
    if agent_record.get("started_at"):
        started = datetime.fromisoformat(agent_record["started_at"])
        agent_record["duration_sec"] = round(
            (datetime.now() - started).total_seconds(), 1
        )

    fallback = (
        f"⚠️ {agent_name} analysis was temporarily unavailable. "
        "The system will retry on the next scheduled run. "
        "Please check other sections for actionable insights."
    )
    logger.error(f"  [{agent_name}] FAILED after {MAX_AGENT_RETRIES} attempts: {last_error}")
    return fallback


def _markdown_to_html(text: str) -> str:
    """Convert basic markdown/plain text to simple HTML paragraphs."""
    # Replace newlines with <br> and wrap in paragraphs
    lines = text.strip().split("\n")
    html_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            html_lines.append("<br>")
        elif line.startswith("**") and line.endswith("**"):
            html_lines.append(f"<p><strong>{line.strip('*')}</strong></p>")
        elif line.startswith("- ") or line.startswith("* "):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line.startswith("#"):
            clean = line.lstrip("#").strip()
            html_lines.append(f"<p><strong>{clean}</strong></p>")
        else:
            # Bold markdown patterns
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            html_lines.append(f"<p>{line}</p>")
    return "\n".join(html_lines)


def _compile_and_send_email(agent_results: dict, today: str) -> str:
    """Compile agent results into HTML email using Jinja2 and send via SMTP."""

    # Load the Jinja2 template
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("briefing_email.html")

    # Render the template with agent results
    html_content = template.render(
        report_date=today,
        market_overview=_markdown_to_html(agent_results.get("market_intel", "No data available.")),
        ml_model_health=_markdown_to_html(agent_results.get("ml_analysis", "No data available.")),
        trade_opportunities=_markdown_to_html(agent_results.get("strategy", "No data available.")),
        tech_signals=_markdown_to_html(agent_results.get("tech_signals", "No data available.")),
        forex_outlook=_markdown_to_html(agent_results.get("forex", "No data available.")),
        risk_warnings=_markdown_to_html(agent_results.get("risk", "No data available.")),
        cross_strategy=_markdown_to_html(agent_results.get("cross_strategy", "No data available.")),
    )

    # Send the email
    subject = f"Daily Trading Briefing - {today}"
    try:
        # Get recipients grouped by type (TO/CC/BCC)
        by_type = get_email_recipients_by_type("daily_briefing")
        all_recipients = by_type["TO"] + by_type["CC"] + by_type["BCC"]
        if not all_recipients:
            return "Error: No email recipients configured in database or .env"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>" if EMAIL_FROM_NAME else EMAIL_FROM
        if by_type["TO"]:
            msg["To"] = ", ".join(by_type["TO"])
        if by_type["CC"]:
            msg["Cc"] = ", ".join(by_type["CC"])
        if by_type["BCC"]:
            msg["Bcc"] = ", ".join(by_type["BCC"])

        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, all_recipients, msg.as_string())

        return f"Email sent successfully to {len(all_recipients)} recipients with subject: {subject}"

    except Exception as e:
        return f"Error sending email: {str(e)}"


def run_daily_briefing_with_rate_limiting() -> str:
    """
    Run the full Daily Briefing with rate-limit-safe execution.

    Stability features:
      - Pre-flight checks (SQL, API key, data freshness, email config)
      - Per-agent try/except with retry (MAX_AGENT_RETRIES attempts)
      - Output validation (detects error strings, empty results)
      - Graceful degradation (failed agents → fallback text in email)
      - Structured JSON run history with per-agent timing
      - Detailed log file per day
    """

    run_record = _new_run_record()
    pipeline_start = datetime.now()
    today = date.today().strftime("%B %d, %Y")
    agent_results = {}

    # =========================================================================
    # Pre-Flight Checks
    # =========================================================================
    can_proceed, preflight_results = run_preflight_checks(verbose=True)
    run_record["preflight_passed"] = can_proceed
    run_record["preflight_warnings"] = [
        str(r) for r in preflight_results if not r.passed
    ]

    if not can_proceed:
        run_record["status"] = "failed"
        run_record["error"] = "Pre-flight checks failed (critical)"
        run_record["finished_at"] = datetime.now().isoformat()
        run_record["total_duration_sec"] = round(
            (datetime.now() - pipeline_start).total_seconds(), 1
        )
        save_run_record(run_record)
        logger.error("Pipeline ABORTED due to critical pre-flight failures.")
        return "Pipeline aborted: critical pre-flight checks failed."

    # =========================================================================
    # Agent Pipeline — 8 agents with retry, timing, and graceful degradation
    # =========================================================================

    # Define all agents as a list of (key, number, label, create_fn, task_desc, expected)
    agent_pipeline = [
        (
            "market_intel", "1/7", "Market Intelligence",
            create_market_intel_agent,
            (
                f"Today is {today}. Run the nasdaq_market_summary and nse_market_summary queries. "
                "Provide a CONCISE summary (under 200 words) with:\n"
                "1. Market breadth (stocks up vs down) for each market\n"
                "2. Average daily change\n"
                "3. Overall sentiment (Bullish/Bearish/Neutral)"
            ),
            "Concise market summary under 200 words with key stats.",
        ),
        (
            "ml_analysis", "2/7", "ML Model Analyst",
            create_ml_analyst_agent,
            (
                f"Today is {today}. Run these queries and provide a CONCISE scorecard (under 300 words):\n"
                "1. Run model_accuracy_last_7_days - report Strategy 2 AI price-prediction model accuracy\n"
                "2. Run strategy1_nasdaq_ml_summary - NASDAQ ML classifier daily run stats (from summary table)\n"
                "3. Run strategy1_nse_ml_summary - NSE ML classifier daily run stats (from summary table)\n"
                "4. Run strategy1_forex_ml_summary - Forex ML classifier signal counts and confidence\n\n"
                "Format as TWO sections:\n"
                "**Strategy 2 (AI Price Predictor)**: Each model accuracy %, best model, degradation warnings\n"
                "**Strategy 1 (ML Classifier)**: NASDAQ buy/sell counts + confidence, "
                "NSE buy/sell counts + confidence + accuracy rates, Forex buy/sell counts + confidence"
            ),
            "Concise dual-strategy model scorecard under 300 words covering NASDAQ, NSE, and Forex.",
        ),
        (
            "tech_signals", "3/7", "Technical Signal",
            create_tech_signal_agent,
            (
                f"Today is {today}. Run the active_signals_today query. "
                "Provide a CONCISE summary (under 200 words) with:\n"
                "1. Number of active BULLISH vs BEARISH signals\n"
                "2. Top 5 strongest signals with ticker, trade_tier, technical_combo, "
                "and AI prediction percentage\n"
                "3. Which technical indicators are most active today"
            ),
            "Concise signal summary under 200 words with trade tiers.",
        ),
        (
            "strategy", "4/7", "Strategy & Trade",
            create_strategy_trade_agent,
            (
                f"Today is {today}. Run these queries and provide a CONCISE summary (under 250 words):\n"
                "1. Run top_tier1_opportunities - Top TIER 1 trade setups across both markets\n"
                "2. Run top_tier2_opportunities - Top TIER 2 trade setups across both markets\n"
                "3. Run tier_summary_today - Overview by market\n\n"
                "Provide a focused summary on AI + Technical Combo signals:\n"
                "- Top 10 TIER 1 opportunities with ticker, market, direction (BULLISH/BEARISH), "
                "trade_tier (win rate %), AI prediction %, and technical combo\n"
                "- If less than 10 TIER 1 signals, include top TIER 2 signals to reach 10 total\n"
                "- Summary stats: Total TIER 1 vs TIER 2 count by market (NASDAQ/NSE)"
            ),
            "Concise AI + Technical Combo trade opportunities under 250 words, focused on TIER 1.",
        ),
        (
            "forex", "5/7", "Forex Analysis",
            create_forex_agent,
            (
                f"Today is {today}. Run the single comprehensive query:\n\n"
                "1. forex_comprehensive_analysis - Returns ALL forex data in one query:\n"
                "   - Latest rates (OHLC, daily change, 50d/200d MA)\n"
                "   - Weekly stats (week high/low/open/close)\n"
                "   - ML predictions (Buy/Sell/Hold with confidence %)\n"
                "   - Technical indicators (RSI, MACD, BB, Stochastic with signals)\n"
                "   - Technical consensus score & signal\n"
                "   - Support/resistance levels with distance %\n"
                "   - Crossover signals (BB, MACD, RSI, SMA, Stoch, Fib, Pattern)\n"
                "   - Recent patterns (last 7 days)\n"
                "   - Technical vs ML agreement status\n\n"
                "Provide a CONCISE summary (under 350 words) structured as:\n\n"
                "**Technical Indicator Dashboard** (PRIMARY):\n"
                "For each pair: RSI (reading + signal), MACD signal, BB position, Stochastic signal, "
                "and TECHNICAL CONSENSUS (Strong Buy/Buy/Hold/Sell/Strong Sell based on tech_score)\n\n"
                "**Support & Resistance Levels**:\n"
                "Key S/R for USD/INR and major pairs — distance from current price to key levels\n\n"
                "**Recent Signals & Patterns**:\n"
                "Crossover signals and chart patterns from the last 7 days\n\n"
                "**Technical vs ML Agreement** (CONFIRMATION):\n"
                "For each pair: technical consensus vs ML prediction — "
                "ALIGNED pairs = HIGH CONVICTION (actionable), CONFLICTING = CAUTION\n\n"
                "Focus on USD/INR. Highlight pairs where multiple technical indicators AND ML agree."
            ),
            (
                "Concise forex technical + ML analysis under 350 words. Lead with technical "
                "indicators (RSI, MACD, BB, Stochastic), show support/resistance, crossovers, "
                "patterns, then ML confirmation. Flag ALIGNED pairs as high-conviction trades."
            ),
        ),
        (
            "risk", "6/7", "Risk Assessment",
            create_risk_agent,
            (
                f"Today is {today}. Run these queries and provide a CONCISE summary (under 200 words):\n"
                "1. Run high_risk_positions - find stocks where ML classifier and technical signals CONFLICT\n"
                "2. Run conflicting_signals - find stocks where Strategy 1 and Strategy 2 disagree on direction\n\n"
                "Provide:\n"
                "1. Number of conflicting/misaligned positions across strategies\n"
                "2. Key caution flags (list specific tickers where strategies disagree)\n"
                "3. Overall risk rating (Low/Medium/High) based on number of conflicts"
            ),
            "Concise risk assessment under 200 words with conflict details.",
        ),
        (
            "cross_strategy", "7/7", "Cross-Strategy Analysis",
            create_cross_strategy_agent,
            (
                f"Today is {today}. Run these 2 queries:\n\n"
                "1. nse_all_categories - NSE 500 aligned stocks across all 4 price categories\n"
                "2. nasdaq_all_categories - NASDAQ 100 aligned stocks across all 4 price categories\n\n"
                "Each query returns up to 10 stocks per category (Cat1_Below20, Cat2_20to100, "
                "Cat3_100to200, Cat4_Above200), already sorted by ML confidence.\n\n"
                "STRATEGY DEFINITIONS:\n"
                "- Strategy 1: ML Classifier (ml_nse_trading_predictions / ml_trading_predictions)\n"
                "  → Buy/Sell signals with confidence %, signal strength\n"
                "- Strategy 2: AI 3-day Price Predictions (ai_prediction_history with days_ahead=3)\n"
                "  → Predicted price → BULLISH if up, BEARISH if down\n"
                "- ALIGNED: Both agree on direction (ML Buy + AI Bullish OR ML Sell + AI Bearish)\n\n"
                "Provide a CONCISE summary (under 400 words) with TWO sections:\n\n"
                "**NSE 500 Cross-Strategy (4 Price Categories):**\n"
                "Group results by price_category field. For each category, show top stocks:\n"
                "- Cat1 (<₹20): List top stocks with Ticker, ML Signal, Confidence%, AI Direction, Change%, Price→Target\n"
                "- Cat2 (₹20-₹100): Same format\n"
                "- Cat3 (₹100-₹200): Same format\n"
                "- Cat4 (>₹200): Same format\n\n"
                "**NASDAQ 100 Cross-Strategy (4 Price Categories):**\n"
                "Group results by price_category field. For each category, show top stocks:\n"
                "- Cat1 (<$20): List top stocks with same format\n"
                "- Cat2 ($20-$100): Same format\n"
                "- Cat3 ($100-$200): Same format\n"
                "- Cat4 (>$200): Same format\n\n"
                "Highlight these as highest-conviction trades where both ML and AI agree."
            ),
            (
                "Concise cross-strategy summary under 400 words with TWO sections: "
                "(1) NSE with 4 price categories showing aligned stocks per category, and "
                "(2) NASDAQ with 4 price categories showing aligned stocks per category. "
                "All stocks have Strategy 1 (ML Classifier) and Strategy 2 (AI Price Predictions) agreeing."
            ),
        ),
    ]

    # Run each agent with retry + timing + graceful degradation
    for idx, (key, number, label, create_fn, task_desc, expected) in enumerate(agent_pipeline):
        agent_rec = _new_agent_record(label)
        run_record["agent_details"][key] = agent_rec

        logger.info(f"\n{'=' * 60}")
        logger.info(f"AGENT {number}: {label} Agent")
        logger.info(f"{'=' * 60}")

        agent_results[key] = _run_agent_with_retry(
            agent_name=label,
            create_fn=create_fn,
            task_description=task_desc,
            expected_output=expected,
            agent_record=agent_rec,
        )

        if agent_rec["status"] == "success":
            run_record["agents_succeeded"] += 1
        else:
            run_record["agents_failed"] += 1

        # Rate-limit pause (skip after last agent)
        if idx < len(agent_pipeline) - 1:
            logger.info(f"--- {label} complete. Pausing {PAUSE_SECONDS}s for rate limit ---")
            time.sleep(PAUSE_SECONDS)

    # =========================================================================
    # Compile and Send Report (using Jinja2, no LLM needed)
    # =========================================================================
    logger.info(f"\n{'=' * 60}")
    logger.info("COMPILING REPORT & SENDING EMAIL")
    logger.info(f"{'=' * 60}")

    result = _compile_and_send_email(agent_results, today)
    run_record["email_sent"] = "successfully" in result.lower()
    if run_record["email_sent"]:
        recipients = get_email_recipients("daily_briefing")
        run_record["email_recipients"] = recipients

    # =========================================================================
    # Finalize Run Record
    # =========================================================================
    run_record["finished_at"] = datetime.now().isoformat()
    run_record["total_duration_sec"] = round(
        (datetime.now() - pipeline_start).total_seconds(), 1
    )

    if run_record["agents_failed"] == 0:
        run_record["status"] = "success"
    elif run_record["agents_succeeded"] > 0:
        run_record["status"] = "partial"
    else:
        run_record["status"] = "failed"

    save_run_record(run_record)

    # Print summary
    logger.info(f"\n{'=' * 60}")
    logger.info("RUN SUMMARY")
    logger.info(f"{'=' * 60}")
    logger.info(f"  Status     : {run_record['status'].upper()}")
    logger.info(f"  Duration   : {run_record['total_duration_sec']}s")
    logger.info(f"  Agents OK  : {run_record['agents_succeeded']}/8")
    logger.info(f"  Agents Fail: {run_record['agents_failed']}/8")
    logger.info(f"  Email Sent : {run_record['email_sent']}")

    failed_names = [
        v["agent_name"] for v in run_record["agent_details"].values()
        if v["status"] == "failed"
    ]
    if failed_names:
        logger.warning(f"  Failed     : {', '.join(failed_names)}")

    logger.info(f"{'=' * 60}")

    return result
