"""
Agent 6: Risk Assessment Agent
Role: Risk Manager
Evaluates risk by finding conflicting signals between Strategy 1
(ML Classifier) and Strategy 2 (AI + Technical), flags misalignments,
and reviews portfolio positions.
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import RISK_QUERIES
from tools.sql_tool import PredefinedSQLQueryTool
from tools.calculation_tools import PnLCalculatorTool


def create_risk_agent() -> Agent:
    """Create and return the Risk Assessment Agent."""

    risk_sql_tool = PredefinedSQLQueryTool(
        name="risk_data_query",
        description=(
            "Query risk and portfolio data from SQL Server. Available queries: "
            + ", ".join(RISK_QUERIES.keys())
            + ". Use the query name as input."
        ),
        query_set=RISK_QUERIES,
    )

    pnl_tool = PnLCalculatorTool()

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=1500,
        temperature=0.2,
    )

    agent = Agent(
        role="Risk Manager",
        goal=(
            "Evaluate the overall risk posture by finding positions where "
            "Strategy 1 (ML Classifier) and Strategy 2 (AI + Technical) "
            "CONFLICT on direction. Identify stocks where one strategy says "
            "Buy but the other says Sell. Also check for misaligned signals "
            "within Strategy 2 (ML signal vs technical signal conflict). "
            "Provide an overall risk rating based on the number and severity "
            "of conflicts."
        ),
        backstory=(
            "You are a certified risk manager (FRM) who focuses on finding "
            "divergences between independent trading systems. When Strategy 1 "
            "(ML classifier: Overbought/Sell vs Oversold/Buy) disagrees with "
            "Strategy 2 (AI price prediction + technical combos: BULLISH vs "
            "BEARISH), that stock is a caution flag. You also look for stocks "
            "where the ML confidence is high but the technical signal points "
            "the other way. You always list specific tickers with conflict "
            "details so the trader knows exactly what to watch out for."
        ),
        tools=[risk_sql_tool, pnl_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=AGENT_MAX_ITER,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
