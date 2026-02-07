"""
Agent 4: Strategy & Trade Agent
Role: Trading Strategy Manager
Finds the best trade opportunities by combining AI predictions
with technical signals from strategy1_tracking.
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
            "Find and rank the top trade opportunities for today. "
            "Focus on TIER 1 and TIER 2 signals where AI predictions "
            "and technical analysis are ALIGNED. Present each opportunity "
            "with its ticker, direction (BULLISH/BEARISH), AI confidence, "
            "technical score, combined score, stop-loss, take-profit, "
            "risk/reward ratio, and any warning flags. "
            "Also summarize the overall strategy performance by tier."
        ),
        backstory=(
            "You are a senior trading strategist who combines quantitative "
            "AI model predictions with classical technical analysis to find "
            "the highest-probability trade setups. You understand that the "
            "best trades occur when AI predictions and technical indicators "
            "agree (ALIGNED signals). You are disciplined about risk management "
            "-- always considering stop-loss, take-profit, position sizing, "
            "and risk/reward ratios. You flag conflicting signals and high-risk "
            "setups so the trader can make informed decisions."
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
