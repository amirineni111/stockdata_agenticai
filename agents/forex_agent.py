"""
Agent 5: Forex Analysis Agent
Role: Forex Market Specialist
Analyzes currency pair movements and ML predictions for forex.
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import FOREX_QUERIES
from tools.sql_tool import PredefinedSQLQueryTool


def create_forex_agent() -> Agent:
    """Create and return the Forex Analysis Agent."""

    forex_sql_tool = PredefinedSQLQueryTool(
        name="forex_data_query",
        description=(
            "Query forex market data from SQL Server. Available queries: "
            + ", ".join(FOREX_QUERIES.keys())
            + ". Use the query name as input."
        ),
        query_set=FOREX_QUERIES,
    )

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=1500,
        temperature=0.3,
    )

    agent = Agent(
        role="Forex Market Specialist",
        goal=(
            "Analyze the latest forex rates and ML predictions for all "
            "tracked currency pairs. Focus especially on USD/INR trends. "
            "Report the latest rates, daily changes, position relative to "
            "50-day and 200-day moving averages, and any ML model signals "
            "(buy/sell/hold) with their confidence levels. "
            "Provide a concise forex outlook."
        ),
        backstory=(
            "You are an experienced forex analyst covering major and "
            "exotic currency pairs with a special focus on USD/INR for "
            "Indian market exposure. You combine fundamental analysis "
            "(macro trends, interest rate differentials) with technical "
            "levels (moving averages, support/resistance) and ML model "
            "predictions to form a comprehensive view. You present your "
            "analysis in a structured, actionable format."
        ),
        tools=[forex_sql_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=AGENT_MAX_ITER,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
