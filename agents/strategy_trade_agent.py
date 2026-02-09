"""
Agent 4: Strategy & Trade Agent
Role: Trading Strategy Manager
Finds the best trade opportunities from BOTH strategies:
  - Strategy 2: AI price prediction + Technical combos (TIER 1/2 classifications)
  - Strategy 1: ML Buy/Sell classifier top signals (NASDAQ + NSE)
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import STRATEGY_TRADE_QUERIES
from tools.sql_tool import PredefinedSQLQueryTool
from tools.calculation_tools import RiskRewardCalculatorTool


def create_strategy_trade_agent() -> Agent:
    """Create and return the Strategy & Trade Agent."""

    strategy_sql_tool = PredefinedSQLQueryTool(
        name="strategy_trade_data_query",
        description=(
            "Query strategy and trade data from SQL Server. Available queries: "
            + ", ".join(STRATEGY_TRADE_QUERIES.keys())
            + ". Use the query name as input."
        ),
        query_set=STRATEGY_TRADE_QUERIES,
    )

    risk_reward_tool = RiskRewardCalculatorTool()

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=1500,
        temperature=0.3,
    )

    agent = Agent(
        role="Trading Strategy Manager",
        goal=(
            "Find and rank the top trade opportunities from BOTH strategies:\n"
            "Strategy 2 (AI + Technical): Focus on TIER 1 signals where AI "
            "predictions and technical indicators are ALIGNED, with ticker, "
            "direction, trade_tier, AI prediction %, and technical combo.\n"
            "Strategy 1 (ML Classifier): Top Buy/Sell signals from the ML "
            "classifier with ticker, confidence %, RSI category, and strength.\n"
            "Present both sets of opportunities clearly."
        ),
        backstory=(
            "You are a senior trading strategist who evaluates TWO independent "
            "strategy pipelines. Strategy 2 combines AI price prediction models "
            "with technical indicator combos (MACD, RSI, BB, Stochastic, Fibonacci, "
            "Pattern) and classifies trades into TIER 1 ULTRA (76-93% win rate) "
            "and TIER 2 MODERATE tiers. Strategy 1 uses ML classifiers that generate "
            "Overbought (Sell) / Oversold (Buy) signals with confidence percentages "
            "and RSI-based categorization. You always present BOTH strategy outputs "
            "so the trader can see the full picture."
        ),
        tools=[strategy_sql_tool, risk_reward_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=AGENT_MAX_ITER,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
