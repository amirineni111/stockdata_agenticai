"""
Agent 6: Risk Assessment Agent
Role: Risk Manager
Evaluates portfolio risk, identifies concentration issues,
flags warnings and conflicting signals.
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
            "Evaluate the overall risk posture across all markets. "
            "Identify high-risk positions where model disagreement is high, "
            "flag CONFLICTING signals where AI and technical analysis disagree, "
            "review active trading alerts, check portfolio positions and P&L, "
            "and provide an overall risk summary. Also summarize family assets "
            "for a holistic wealth view."
        ),
        backstory=(
            "You are a certified risk manager (FRM) with experience in "
            "both institutional and personal portfolio risk management. "
            "You understand that the biggest risk is not a single bad trade "
            "but rather hidden correlations, concentration risk, and ignoring "
            "warning signals. You are meticulous about identifying conflicting "
            "signals, high model disagreement, and positions approaching "
            "stop-loss levels. You always present risk in both absolute "
            "dollar terms and percentage terms."
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
