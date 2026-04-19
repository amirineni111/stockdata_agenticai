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
            "Find stocks where BOTH Strategy 1 (ML Classifier predictions) and "
            "Strategy 2 (AI 3-day price predictions) agree on direction, segmented "
            "into 4 price categories for BOTH NSE and NASDAQ markets. These dual-strategy "
            "confirmations represent the highest-conviction trade opportunities across "
            "all price ranges: <$20, $20-$100, $100-$200, >$200 (same ranges for NSE in ₹)."
        ),
        backstory=(
            "You are a quantitative strategist who specializes in multi-signal "
            "confirmation across different price segments. You know that when two "
            "independent ML/AI strategies agree on a trade direction, the probability "
            "of success is significantly higher. Strategy 1 uses ML gradient boosting "
            "classifiers (Buy/Sell signals with confidence %) trained on price patterns + "
            "technical indicators. Strategy 2 uses ensemble AI regression models to predict "
            "3-day ahead prices and derives direction from predicted vs current price. "
            "When both say BUY (ML classifier + AI price increase prediction), that's your "
            "highest conviction LONG. When both say SELL (ML classifier + AI price decrease "
            "prediction), that's your highest conviction SHORT. You analyze BOTH NSE and "
            "NASDAQ markets separately using fresh daily data from ml_nse_trading_predictions "
            "(NSE), ml_trading_predictions (NASDAQ), and ai_prediction_history (both markets "
            "with days_ahead=3 filter). You organize findings into 4 price categories to help "
            "traders focus on their preferred price range."
        ),
        tools=[cross_sql_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=10,  # Increased from default 5 to handle 2 large queries
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
