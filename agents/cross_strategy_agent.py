"""
Agent 7: Cross-Strategy Analysis Agent
Role: Cross-Strategy Analyst
Finds common recommendations between Strategy 1 (AI + Technical Combos)
and Strategy 2 (ML + Signal Alignment) to identify highest-conviction trades.
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import CROSS_STRATEGY_QUERIES
from tools.sql_tool import PredefinedSQLQueryTool


def create_cross_strategy_agent() -> Agent:
    """Create and return the Cross-Strategy Analysis Agent."""

    cross_sql_tool = PredefinedSQLQueryTool(
        name="cross_strategy_query",
        description=(
            "Query cross-strategy data from SQL Server. Available queries: "
            + ", ".join(CROSS_STRATEGY_QUERIES.keys())
            + ". Use the query name as input."
        ),
        query_set=CROSS_STRATEGY_QUERIES,
    )

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=1500,
        temperature=0.2,
    )

    agent = Agent(
        role="Cross-Strategy Analyst",
        goal=(
            "Find stocks that BOTH Strategy 1 (AI + Technical Combos) and "
            "Strategy 2 (ML Forex/Stock classifier) recommend in the same "
            "direction. These dual-strategy confirmations represent the "
            "highest-conviction trade opportunities. Also identify stocks "
            "where the two strategies CONFLICT as caution flags."
        ),
        backstory=(
            "You are a quantitative strategist who specializes in multi-signal "
            "confirmation. You know that when two independent strategies with "
            "different methodologies agree on a trade direction, the probability "
            "of success is significantly higher. Strategy 1 uses AI prediction "
            "models combined with technical indicator combos (MACD, RSI, BB, "
            "Stochastic, Fibonacci, Pattern) and classifies signals into TIER 1 "
            "ULTRA (76-93% win rate) and TIER 2 MODERATE tiers. Strategy 2 uses "
            "ML classification (Buy/Sell with confidence %) combined with RSI "
            "and assigns trade grades (A through D). When both strategies say "
            "SELL on the same stock, that's your highest conviction SHORT."
        ),
        tools=[cross_sql_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=AGENT_MAX_ITER,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
