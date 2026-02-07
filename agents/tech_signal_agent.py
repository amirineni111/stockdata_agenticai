"""
Agent 3: Technical Signal Agent
Role: Technical Analysis Specialist
Identifies active buy/sell signals and tracks historical signal outcomes.
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import TECH_SIGNAL_QUERIES
from tools.sql_tool import PredefinedSQLQueryTool


def create_tech_signal_agent() -> Agent:
    """Create and return the Technical Signal Agent."""

    tech_sql_tool = PredefinedSQLQueryTool(
        name="tech_signal_data_query",
        description=(
            "Query technical signal data from SQL Server. Available queries: "
            + ", ".join(TECH_SIGNAL_QUERIES.keys())
            + ". Use the query name as input."
        ),
        query_set=TECH_SIGNAL_QUERIES,
    )

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=1500,
        temperature=0.2,
    )

    agent = Agent(
        role="Technical Analysis Specialist",
        goal=(
            "Identify the strongest active buy and sell signals from our "
            "technical analysis system. Analyze signal strength scores, "
            "review which indicators (MACD, RSI, Bollinger Bands, Stochastic, "
            "Fibonacci, SMA, Pattern) are triggering, and evaluate the "
            "historical accuracy of signals at 7-day and 14-day horizons. "
            "Highlight the most reliable signal patterns."
        ),
        backstory=(
            "You are a chartered market technician (CMT) with expertise in "
            "multi-indicator technical analysis. You understand how MACD, RSI, "
            "Bollinger Bands, Stochastic oscillators, Fibonacci retracements, "
            "moving averages, and candlestick patterns interact to form "
            "high-probability trade setups. You are rigorous about validating "
            "signals against their historical track record and only highlight "
            "signals with proven reliability."
        ),
        tools=[tech_sql_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=AGENT_MAX_ITER,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
