"""
Conversational AI Stock Assistant
==================================
An interactive chat interface that routes natural language questions
to the appropriate specialist agent (or the general SQL query tool).

This is the "productionized" version of talking to your SQL Server
through an AI assistant -- but now backed by specialized CrewAI agents.

Usage:
    python chat_assistant.py                  # Interactive chat mode
    python chat_assistant.py --query "..."    # Single query mode

Example questions:
    "Which TIER 1 BULLISH signals were generated today?"
    "How did Gradient Boosting perform this week vs Random Forest?"
    "What is the current USD/INR rate?"
    "Show me all stocks where AI and technicals are ALIGNED"
    "What is my total family net worth?"
    "Any high-risk warnings today?"
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import Agent, Crew, Task, Process, LLM
from config.settings import LLM_MODEL, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import (
    MARKET_INTEL_QUERIES,
    ML_ANALYST_QUERIES,
    TECH_SIGNAL_QUERIES,
    STRATEGY_TRADE_QUERIES,
    FOREX_QUERIES,
    RISK_QUERIES,
)
from tools.sql_tool import SQLQueryTool, PredefinedSQLQueryTool
from tools.calculation_tools import (
    AccuracyCalculatorTool,
    PnLCalculatorTool,
    RiskRewardCalculatorTool,
)

# Merge all predefined queries into one combined set
ALL_QUERIES = {}
ALL_QUERIES.update({f"market_{k}": v for k, v in MARKET_INTEL_QUERIES.items()})
ALL_QUERIES.update({f"ml_{k}": v for k, v in ML_ANALYST_QUERIES.items()})
ALL_QUERIES.update({f"tech_{k}": v for k, v in TECH_SIGNAL_QUERIES.items()})
ALL_QUERIES.update({f"strategy_{k}": v for k, v in STRATEGY_TRADE_QUERIES.items()})
ALL_QUERIES.update({f"forex_{k}": v for k, v in FOREX_QUERIES.items()})
ALL_QUERIES.update({f"risk_{k}": v for k, v in RISK_QUERIES.items()})


def create_chat_agent() -> Agent:
    """
    Create a conversational agent that can answer any stock data question
    by routing to predefined queries or generating ad-hoc SQL.
    """

    # Tool 1: Predefined queries (safe, pre-tested)
    predefined_tool = PredefinedSQLQueryTool(
        name="stock_data_query",
        description=(
            "Execute a predefined SQL query against the stock database. "
            "Available queries (use exact name): "
            + ", ".join(sorted(ALL_QUERIES.keys()))
        ),
        query_set=ALL_QUERIES,
    )

    # Tool 2: Ad-hoc SQL queries (flexible, for custom questions)
    adhoc_sql_tool = SQLQueryTool()

    # Tool 3: Calculation tools
    accuracy_tool = AccuracyCalculatorTool()
    pnl_tool = PnLCalculatorTool()
    rr_tool = RiskRewardCalculatorTool()

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=1500,
        temperature=0.3,
    )

    agent = Agent(
        role="Stock Data AI Assistant",
        goal=(
            "Answer any question about the user's stock market data, "
            "ML predictions, technical signals, trading strategies, forex, "
            "portfolio, and family assets. Use predefined queries when "
            "available, and generate ad-hoc SQL for custom questions. "
            "Always provide clear, actionable answers with data."
        ),
        backstory=(
            "You are a highly capable financial data assistant with deep "
            "knowledge of the user's SQL Server database containing 29 tables "
            "of stock market data. You know the schema intimately:\n\n"
            "MARKET DATA:\n"
            "- nasdaq_100_hist_data (ticker, trading_date, open/high/low/close_price, volume)\n"
            "- nse_500_hist_data (same schema as NASDAQ)\n"
            "- nasdaq_100_fundamentals, nse_500_fundamentals\n\n"
            "STRATEGY 2 (AI Price Prediction):\n"
            "- ai_prediction_history (model_name: LR/GB/RF, ticker, predicted_price, actual_price, direction_correct, model_confidence)\n"
            "- ml_technical_indicators (sma, ema, macd, rsi, volatility) - NASDAQ technical\n"
            "- ml_nse_technical_indicators - NSE technical\n\n"
            "STRATEGY 1 (ML Classifier):\n"
            "- ml_trading_predictions (NASDAQ: predicted_signal, confidence_percentage, buy/sell_probability, signal_strength, direction_correct_1d)\n"
            "- ml_nse_trading_predictions (NSE: same + model_name, sector, market_cap_category)\n"
            "- forex_ml_predictions (Forex: predicted_signal BUY/SELL, signal_confidence, prob_buy/sell/hold, direction_correct_1d)\n"
            "- ml_prediction_summary (NASDAQ daily run stats)\n"
            "- ml_nse_predict_summary (NSE daily run stats with model_accuracy, success_rates)\n\n"
            "TECHNICAL SIGNALS:\n"
            "- signal_tracking_history (signal_type, signal_strength, macd/rsi/bb/sma/stoch/fib/pattern_signal, result_7d/14d/30d)\n"
            "- daily_signals_history\n\n"
            "STRATEGY VIEWS:\n"
            "- vw_PowerBI_AI_Technical_Combos (Strategy 2: AI + technical combos, trade_tier TIER 1/2)\n"
            "- vw_strategy2_trade_opportunities (Strategy 1+signals: ML signal + tech alignment, trade_grade A-D)\n"
            "- trade_log, trading_alerts, prediction_watchlist\n\n"
            "FOREX:\n"
            "- forex_hist_data (symbol, close_price, daily_change_pct, fifty_day_avg, two_hundred_day_avg)\n\n"
            "PERSONAL:\n"
            "- portfolio_tracker (ticker, buy_price, buy_qty, status)\n"
            "- family_assets (asset_type, item_name, purchase_value, current_status)\n"
            "- stock_notes\n\n"
            "You prefer using predefined queries (prefixed with market_, ml_, tech_, "
            "strategy_, forex_, risk_) for common questions, and write custom SQL "
            "for anything else. You always explain your findings clearly and concisely."
        ),
        tools=[predefined_tool, adhoc_sql_tool, accuracy_tool, pnl_tool, rr_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=5,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent


def ask_question(agent: Agent, question: str) -> str:
    """Send a question to the chat agent by creating a mini-crew."""
    today = datetime.now().strftime("%B %d, %Y")
    task = Task(
        description=(
            f"Today is {today}. Answer the following user question using your "
            f"SQL query tools. Be concise and data-driven.\n\n"
            f"User Question: {question}"
        ),
        expected_output="A clear, concise answer to the user's question with relevant data.",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        memory=False,
    )

    result = crew.kickoff()
    return result.raw if hasattr(result, "raw") else str(result)


def interactive_chat():
    """Run an interactive chat session."""
    print()
    print("=" * 60, flush=True)
    print("  STOCK DATA AI ASSISTANT", flush=True)
    print("=" * 60, flush=True)
    print(f"  Date: {datetime.now().strftime('%B %d, %Y')}", flush=True)
    print(flush=True)
    print("  Ask me anything about your stock data!", flush=True)
    print("  Examples:", flush=True)
    print('    - "How did the NASDAQ market do today?"', flush=True)
    print('    - "Which ML model is performing best this week?"', flush=True)
    print('    - "Show me TIER 1 trade opportunities"', flush=True)
    print('    - "What is the current USD/INR rate?"', flush=True)
    print(flush=True)
    print("  Type 'quit' or 'exit' to stop.", flush=True)
    print("=" * 60, flush=True)

    print("\n  Initializing AI assistant...", flush=True)
    agent = create_chat_agent()
    print("  Ready! Ask your first question below.\n", flush=True)

    while True:
        try:
            question = input("You >> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print("\n[Thinking...]\n", flush=True)
        try:
            answer = ask_question(agent, question)
            print(f"Assistant: {answer}\n")
        except Exception as e:
            print(f"Error: {e}\n")


def single_query(question: str):
    """Answer a single question and exit."""
    print(f"Question: {question}\n")
    agent = create_chat_agent()
    answer = ask_question(agent, question)
    print(f"Answer:\n{answer}")


def main():
    parser = argparse.ArgumentParser(
        description="Stock Data AI Chat Assistant"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Ask a single question (non-interactive mode)",
    )

    args = parser.parse_args()

    if args.query:
        single_query(args.query)
    else:
        interactive_chat()


if __name__ == "__main__":
    main()
