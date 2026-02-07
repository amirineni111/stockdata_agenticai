"""
SQL Server query tool for CrewAI agents.
Provides a reusable tool that any agent can use to execute SQL queries
against the local SQL Server database via pyodbc.
"""

import pyodbc
from crewai.tools import BaseTool
from pydantic import Field
from typing import Type
from pydantic import BaseModel

from config.settings import get_sql_connection_string


class SQLQueryInput(BaseModel):
    """Input schema for the SQL query tool."""
    query: str = Field(description="The SQL query to execute against the SQL Server database.")


class SQLQueryTool(BaseTool):
    """
    Executes a read-only SQL query against the SQL Server database
    and returns results as a formatted string.
    """
    name: str = "sql_query_tool"
    description: str = (
        "Execute a read-only SQL query against the SQL Server database. "
        "Use this tool to retrieve stock market data, ML predictions, "
        "technical signals, strategy tracking, forex data, portfolio data, "
        "and family assets. Returns results as a formatted text table."
    )
    args_schema: Type[BaseModel] = SQLQueryInput

    def _run(self, query: str) -> str:
        """Execute the SQL query and return formatted results."""
        try:
            conn_str = get_sql_connection_string()
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            cursor.execute(query)

            # Get column names
            columns = [desc[0] for desc in cursor.description]

            # Fetch all rows
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            if not rows:
                return "Query returned no results."

            # Format as readable text table
            result_lines = []
            result_lines.append(" | ".join(columns))
            result_lines.append("-" * len(result_lines[0]))

            for row in rows:
                formatted_values = []
                for val in row:
                    if val is None:
                        formatted_values.append("NULL")
                    else:
                        formatted_values.append(str(val))
                result_lines.append(" | ".join(formatted_values))

            result_lines.append(f"\n({len(rows)} rows returned)")
            return "\n".join(result_lines)

        except pyodbc.Error as e:
            return f"SQL Error: {str(e)}"
        except Exception as e:
            return f"Error executing query: {str(e)}"


class PredefinedSQLQueryInput(BaseModel):
    """Input schema for the predefined SQL query tool."""
    query_name: str = Field(
        description="The name of the predefined query to execute."
    )


class PredefinedSQLQueryTool(BaseTool):
    """
    Executes a predefined SQL query from the sql_queries module.
    Safer than ad-hoc queries since the SQL is pre-written and tested.
    """
    name: str = "predefined_sql_query_tool"
    description: str = (
        "Execute a predefined SQL query by name. Available query sets: "
        "MARKET_INTEL_QUERIES, ML_ANALYST_QUERIES, TECH_SIGNAL_QUERIES, "
        "STRATEGY_TRADE_QUERIES, FOREX_QUERIES, RISK_QUERIES. "
        "Provide the query name (e.g., 'nasdaq_top_movers', 'model_accuracy_last_7_days')."
    )
    args_schema: Type[BaseModel] = PredefinedSQLQueryInput
    query_set: dict = Field(default_factory=dict)

    def _run(self, query_name: str) -> str:
        """Execute a predefined query by name."""
        if query_name not in self.query_set:
            available = ", ".join(self.query_set.keys())
            return (
                f"Query '{query_name}' not found. "
                f"Available queries: {available}"
            )

        sql = self.query_set[query_name]
        sql_tool = SQLQueryTool()
        return sql_tool._run(query=sql)
