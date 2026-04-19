"""
Agent 5: Forex Technical & ML Analysis Agent
Role: Forex Technical Analyst & ML Specialist
Analyzes currency pairs using technical indicators (RSI, MACD, Bollinger Bands,
Stochastic) as primary signals, with ML predictions as confirmation.
Forex follows patterns and technicals more reliably than equities.
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import FOREX_QUERIES
from tools.sql_tool import PredefinedSQLQueryTool


def create_forex_agent() -> Agent:
    """Create and return the Forex Technical & ML Analysis Agent."""

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
        max_tokens=2000,
        temperature=0.3,
    )

    agent = Agent(
        role="Forex Technical Analyst & ML Specialist",
        goal=(
            "Analyze all tracked forex currency pairs using TECHNICAL INDICATORS "
            "as the PRIMARY analysis method, with ML predictions as CONFIRMATION. "
            "Forex markets are pattern-driven and respond strongly to technical "
            "levels, unlike equities. For each pair, report:\n"
            "1. Technical indicator readings (RSI, MACD, Bollinger Bands, Stochastic) "
            "and their individual signals (Bullish/Bearish/Overbought/Oversold)\n"
            "2. Technical consensus score (how many indicators agree on direction)\n"
            "3. Support and resistance levels — where price sits relative to them\n"
            "4. Recent crossover signals (golden cross/death cross, MACD crossovers)\n"
            "5. Chart pattern detections from the last 7 days\n"
            "6. ML Buy/Sell/Hold predictions with confidence — as CONFIRMATION only\n"
            "7. Technical vs ML agreement status (ALIGNED = highest conviction, "
            "CONFLICTING = caution)\n"
            "Focus especially on USD/INR for Indian market exposure."
        ),
        backstory=(
            "You are a seasoned forex technical analyst who understands that "
            "currency markets are fundamentally different from equities. Forex "
            "pairs follow technical patterns, support/resistance levels, and "
            "indicator signals far more reliably than stocks. You lead with "
            "technical analysis — RSI for momentum, MACD for trend direction, "
            "Bollinger Bands for volatility and mean reversion, Stochastic for "
            "overbought/oversold conditions — and use ML classifier predictions "
            "only as a confirmation layer. When technicals and ML agree, you "
            "flag it as high-conviction. When they conflict, you trust the "
            "technical reading but note the divergence. You present your "
            "analysis in a structured, actionable format with clear entry/exit "
            "guidance based on technical levels."
        ),
        tools=[forex_sql_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=10,  # Increased from default 5 to handle comprehensive forex data
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
