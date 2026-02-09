"""
Agent 2: ML Model Analyst Agent
Role: Machine Learning Performance Analyst
Evaluates accuracy and health of:
  - Strategy 2: AI Price Prediction models (Linear Regression, Gradient Boosting, Random Forest)
  - Strategy 1: ML Buy/Sell Classifier models (NASDAQ + NSE + Forex)
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from config.sql_queries import ML_ANALYST_QUERIES
from tools.sql_tool import PredefinedSQLQueryTool
from tools.calculation_tools import AccuracyCalculatorTool


def create_ml_analyst_agent() -> Agent:
    """Create and return the ML Model Analyst Agent."""

    ml_sql_tool = PredefinedSQLQueryTool(
        name="ml_model_data_query",
        description=(
            "Query ML model performance data from SQL Server. Available queries: "
            + ", ".join(ML_ANALYST_QUERIES.keys())
            + ". Use the query name as input."
        ),
        query_set=ML_ANALYST_QUERIES,
    )

    accuracy_tool = AccuracyCalculatorTool()

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=1500,
        temperature=0.2,
    )

    agent = Agent(
        role="Machine Learning Performance Analyst",
        goal=(
            "Evaluate BOTH prediction strategies:\n"
            "Strategy 2 (AI Price Predictor): Accuracy of Linear Regression, "
            "Gradient Boosting, and Random Forest models for price direction.\n"
            "Strategy 1 (ML Classifier): Health of Buy/Sell classifier for "
            "NASDAQ (ml_trading_predictions), NSE (ml_nse_trading_predictions), "
            "and Forex (forex_ml_predictions) including signal counts, "
            "confidence levels, and accuracy rates."
        ),
        backstory=(
            "You are a quantitative analyst specializing in ML model monitoring "
            "for financial prediction systems. You monitor TWO separate strategy "
            "pipelines: Strategy 2 uses 3 regression models to predict price "
            "direction (direction_correct metric), while Strategy 1 uses ML "
            "classifiers to generate Buy/Sell signals with confidence percentages "
            "for NASDAQ, NSE, and Forex markets. You always report on BOTH "
            "strategies with concrete numbers across all three markets, "
            "highlighting any degradation or divergence."
        ),
        tools=[ml_sql_tool, accuracy_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=AGENT_MAX_ITER,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
        inject_date=True,
    )

    return agent
