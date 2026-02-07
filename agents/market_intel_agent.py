"""
Agent 1: Market Intelligence Agent
Role: Senior Market Analyst
Analyzes latest price action, volume patterns, and market trends
across NSE 500, NASDAQ 100.
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import MARKET_INTEL_QUERIES
from tools.sql_tool import PredefinedSQLQueryTool


def create_market_intel_agent() -> Agent:
    """Create and return the Market Intelligence Agent."""

    # Create the predefined SQL tool scoped to market intel queries
    market_sql_tool = PredefinedSQLQueryTool(
        name="market_data_query",
        description=(
            "Query market data from SQL Server. Available queries: "
            + ", ".join(MARKET_INTEL_QUERIES.keys())
            + ". Use the query name as input."
        ),
        query_set=MARKET_INTEL_QUERIES,
    )

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=1500,
        temperature=0.3,
    )

    agent = Agent(
        role="Senior Market Analyst",
        goal=(
            "Analyze the latest market data for NASDAQ 100 and NSE 500 stocks. "
            "Identify the overall market trend (bullish/bearish/neutral), "
            "highlight the top movers (biggest gainers and losers), "
            "and summarize the market breadth (stocks up vs down)."
        ),
        backstory=(
            "You are a veteran market analyst with 20 years of experience "
            "tracking both US (NASDAQ) and Indian (NSE) equity markets. "
            "You excel at quickly identifying market regimes, spotting "
            "unusual activity, and providing concise market summaries "
            "that busy traders can act on immediately. You always provide "
            "data-driven observations, not opinions."
        ),
        tools=[market_sql_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=AGENT_MAX_ITER,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
