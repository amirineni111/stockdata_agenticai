"""
Agent 8: Fair Value / Valuation Agent
Role: Fundamental Valuation Analyst
Computes and presents fair value estimates using multiple valuation models
(Graham Number, PEG, Forward Earnings, EPV) for NASDAQ and NSE stocks.
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import VALUATION_QUERIES
from tools.sql_tool import PredefinedSQLQueryTool


def create_valuation_agent() -> Agent:
    """Create and return the Fair Value / Valuation Agent."""

    valuation_sql_tool = PredefinedSQLQueryTool(
        name="valuation_query",
        description=(
            "Query fair value estimates from SQL Server. Available queries: "
            + ", ".join(VALUATION_QUERIES.keys())
            + ". Use the query name as input."
        ),
        query_set=VALUATION_QUERIES,
    )

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=1500,
        temperature=0.2,
    )

    agent = Agent(
        role="Fundamental Valuation Analyst",
        goal=(
            "Identify the most undervalued stocks in NASDAQ 100 and NSE 500 "
            "using four valuation models: Graham Number, PEG Fair Value, "
            "Forward Earnings Value, and Earnings Power Value. Present the "
            "top 20 undervalued stocks per market with their composite fair "
            "value, implied current price, margin of safety, and valuation "
            "verdict. Highlight stocks with the highest margin of safety as "
            "the best value opportunities."
        ),
        backstory=(
            "You are a CFA-certified fundamental valuation analyst who "
            "specializes in multi-model intrinsic value estimation. You use "
            "four complementary approaches: (1) Graham Number — Benjamin "
            "Graham's conservative formula sqrt(22.5 × EPS × Book Value), "
            "(2) PEG Fair Value — fair P/E equals earnings growth rate, "
            "(3) Forward Earnings Value — forward EPS × sector average P/E, "
            "and (4) Earnings Power Value (EPV) — current earnings capitalized "
            "at 10% WACC with no growth assumption. You combine all available "
            "models into a composite fair value and compute the margin of "
            "safety vs the implied current price. A positive margin of safety "
            "means the stock is trading BELOW fair value (undervalued). You "
            "present findings for BOTH NSE and NASDAQ markets separately."
        ),
        tools=[valuation_sql_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=AGENT_MAX_ITER,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
