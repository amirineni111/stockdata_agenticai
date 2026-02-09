"""
Daily Briefing Crew - Master Orchestrator
Assembles all specialist agents into a CrewAI pipeline.

Architecture:
  Runs each agent independently with rate-limit-safe delays,
  then compiles all findings via Jinja2 template and sends email.
"""

import time
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from crewai import Crew, Task, Process
from datetime import date
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
)


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
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>" if EMAIL_FROM_NAME else EMAIL_FROM
        msg["To"] = EMAIL_TO

        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO.split(","), msg.as_string())

        return f"Email sent successfully to {EMAIL_TO} with subject: {subject}"

    except Exception as e:
        return f"Error sending email: {str(e)}"


def run_daily_briefing_with_rate_limiting() -> str:
    """
    Run the full Daily Briefing with rate-limit-safe execution.
    Each agent runs independently with 60-second pauses between them
    to respect the 10k tokens/minute API limit.
    The final report is compiled with Jinja2 (no LLM needed).
    """

    today = date.today().strftime("%B %d, %Y")
    PAUSE_SECONDS = 60  # pause between agents to reset rate limit window
    agent_results = {}

    # =========================================================================
    # Agent 1: Market Intelligence
    # =========================================================================
    print("\n" + "=" * 60)
    print("AGENT 1/7: Market Intelligence Agent")
    print("=" * 60)

    market_intel_agent = create_market_intel_agent()
    agent_results["market_intel"] = _run_single_agent(
        agent=market_intel_agent,
        task_description=(
            f"Today is {today}. Run the nasdaq_market_summary and nse_market_summary queries. "
            "Provide a CONCISE summary (under 200 words) with:\n"
            "1. Market breadth (stocks up vs down) for each market\n"
            "2. Average daily change\n"
            "3. Overall sentiment (Bullish/Bearish/Neutral)"
        ),
        expected_output="Concise market summary under 200 words with key stats.",
    )

    print(f"\n--- Market Intel complete. Pausing {PAUSE_SECONDS}s for rate limit ---")
    time.sleep(PAUSE_SECONDS)

    # =========================================================================
    # Agent 2: ML Model Analyst
    # =========================================================================
    print("\n" + "=" * 60)
    print("AGENT 2/7: ML Model Analyst Agent")
    print("=" * 60)

    ml_analyst_agent = create_ml_analyst_agent()
    agent_results["ml_analysis"] = _run_single_agent(
        agent=ml_analyst_agent,
        task_description=(
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
        expected_output="Concise dual-strategy model scorecard under 300 words covering NASDAQ, NSE, and Forex.",
    )

    print(f"\n--- ML Analysis complete. Pausing {PAUSE_SECONDS}s for rate limit ---")
    time.sleep(PAUSE_SECONDS)

    # =========================================================================
    # Agent 3: Technical Signal Agent
    # =========================================================================
    print("\n" + "=" * 60)
    print("AGENT 3/7: Technical Signal Agent")
    print("=" * 60)

    tech_signal_agent = create_tech_signal_agent()
    agent_results["tech_signals"] = _run_single_agent(
        agent=tech_signal_agent,
        task_description=(
            f"Today is {today}. Run the active_signals_today query. "
            "Provide a CONCISE summary (under 200 words) with:\n"
            "1. Number of active BULLISH vs BEARISH signals\n"
            "2. Top 5 strongest signals with ticker, trade_tier, technical_combo, "
            "and AI prediction percentage\n"
            "3. Which technical indicators are most active today"
        ),
        expected_output="Concise signal summary under 200 words with trade tiers.",
    )

    print(f"\n--- Tech Signals complete. Pausing {PAUSE_SECONDS}s for rate limit ---")
    time.sleep(PAUSE_SECONDS)

    # =========================================================================
    # Agent 4: Strategy & Trade Agent
    # =========================================================================
    print("\n" + "=" * 60)
    print("AGENT 4/7: Strategy & Trade Agent")
    print("=" * 60)

    strategy_trade_agent = create_strategy_trade_agent()
    agent_results["strategy"] = _run_single_agent(
        agent=strategy_trade_agent,
        task_description=(
            f"Today is {today}. Run these queries and provide a CONCISE summary (under 300 words):\n"
            "1. Run top_tier1_opportunities - Strategy 2 TIER 1 trade setups\n"
            "2. Run tier_summary_today - Strategy 2 overview by market\n"
            "3. Run strategy1_nasdaq_top_signals - Strategy 1 ML classifier top NASDAQ signals\n\n"
            "Format as TWO sections:\n"
            "**Strategy 2 (AI + Technical Combos)**: Top 5 TIER 1 with ticker, market, direction, "
            "trade_tier (win rate), AI prediction %, technical combo\n"
            "**Strategy 1 (ML Classifier)**: Top 5 NASDAQ Buy/Sell signals with ticker, signal, "
            "confidence %, RSI category, signal strength"
        ),
        expected_output="Concise dual-strategy trade opportunities under 300 words.",
    )

    print(f"\n--- Strategy complete. Pausing {PAUSE_SECONDS}s for rate limit ---")
    time.sleep(PAUSE_SECONDS)

    # =========================================================================
    # Agent 5: Forex Agent
    # =========================================================================
    print("\n" + "=" * 60)
    print("AGENT 5/7: Forex Analysis Agent")
    print("=" * 60)

    forex_agent = create_forex_agent()
    agent_results["forex"] = _run_single_agent(
        agent=forex_agent,
        task_description=(
            f"Today is {today}. Run these queries and provide a CONCISE summary (under 200 words):\n"
            "1. Run forex_latest_rates - current rates and daily changes\n"
            "2. Run forex_ml_predictions_latest - ML classifier Buy/Sell signals for all pairs\n"
            "3. Run forex_ml_signal_summary - summary of Buy vs Sell counts\n\n"
            "Provide:\n"
            "1. USD/INR current rate and daily change\n"
            "2. Key currency pair movements\n"
            "3. Forex ML Classifier signals: which pairs are BUY vs SELL with confidence %\n"
            "4. Trend vs moving averages"
        ),
        expected_output="Concise forex summary under 200 words with ML signals.",
    )

    print(f"\n--- Forex complete. Pausing {PAUSE_SECONDS}s for rate limit ---")
    time.sleep(PAUSE_SECONDS)

    # =========================================================================
    # Agent 6: Risk Assessment Agent
    # =========================================================================
    print("\n" + "=" * 60)
    print("AGENT 6/7: Risk Assessment Agent")
    print("=" * 60)

    risk_agent = create_risk_agent()
    agent_results["risk"] = _run_single_agent(
        agent=risk_agent,
        task_description=(
            f"Today is {today}. Run these queries and provide a CONCISE summary (under 200 words):\n"
            "1. Run high_risk_positions - find stocks where ML classifier and technical signals CONFLICT\n"
            "2. Run conflicting_signals - find stocks where Strategy 1 and Strategy 2 disagree on direction\n\n"
            "Provide:\n"
            "1. Number of conflicting/misaligned positions across strategies\n"
            "2. Key caution flags (list specific tickers where strategies disagree)\n"
            "3. Overall risk rating (Low/Medium/High) based on number of conflicts"
        ),
        expected_output="Concise risk assessment under 200 words with conflict details.",
    )

    print(f"\n--- Risk complete. Pausing {PAUSE_SECONDS}s for rate limit ---")
    time.sleep(PAUSE_SECONDS)

    # =========================================================================
    # Agent 7: Cross-Strategy Analysis
    # =========================================================================
    print("\n" + "=" * 60)
    print("AGENT 7/7: Cross-Strategy Analysis Agent")
    print("=" * 60)

    cross_strategy_agent = create_cross_strategy_agent()
    agent_results["cross_strategy"] = _run_single_agent(
        agent=cross_strategy_agent,
        task_description=(
            f"Today is {today}. Run the common_stocks_both_strategies query "
            "to find stocks that appear in BOTH Strategy 1 (TIER 1 AI+Technical) "
            "and Strategy 2 (Grade A/B ML+RSI). Then run common_stocks_summary. "
            "Provide a CONCISE summary (under 250 words) with:\n"
            "1. Total number of stocks found in BOTH strategies\n"
            "2. How many are ALIGNED (same direction) vs CONFLICTING\n"
            "3. List each common stock with: ticker, market, S1 direction, S1 tier, "
            "S2 signal, S2 grade, S2 confidence%, and whether ALIGNED or CONFLICTING\n"
            "4. Highlight the ALIGNED stocks as highest-conviction trades\n"
            "5. Flag CONFLICTING stocks as caution zones"
        ),
        expected_output=(
            "Concise cross-strategy summary under 250 words listing common stocks "
            "between both strategies with alignment status."
        ),
    )

    # =========================================================================
    # Compile and Send Report (using Jinja2, no LLM needed)
    # =========================================================================
    print("\n" + "=" * 60)
    print("COMPILING REPORT & SENDING EMAIL")
    print("=" * 60)

    result = _compile_and_send_email(agent_results, today)
    print(f"\n{result}")

    return result
