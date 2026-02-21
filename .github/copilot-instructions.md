# Copilot Instructions — stockdata_agenticai

## Project Context
This is the **Agentic AI** layer of a 7-repo stock trading analytics platform. It runs 7 CrewAI agents that query a shared SQL Server database and compile a daily HTML email briefing using Claude LLM.

## Key Architecture Rules
- This repo is **read-only** against the database — agents only SELECT, never INSERT/UPDATE/DELETE
- All SQL queries are predefined in `config/sql_queries.py` — agents do NOT write ad-hoc SQL in production mode
- Each agent runs as a **mini-crew** (1 agent, 1 task) sequentially with 60s rate-limit pauses
- `report_compiler_agent.py` is **unused** — email compilation is done via Jinja2 in `daily_briefing_crew.py`
- The Cross-Strategy agent is NOT exposed via A2A HTTP API

## Database Notes
- **Server**: `192.168.87.27\MSSQLSERVER01`, **DB**: `stockdata_db`, **Auth**: SQL Auth (`remote_user`)
- Price columns in `nasdaq_100_hist_data` and `nse_500_hist_data` are **VARCHAR** — always CAST to FLOAT
- All configuration comes from `.env` via `config/settings.py`

## Two-Strategy System
- **Strategy 1**: AI price predictions + 6 technical indicators → TIER 1/TIER 2 signals (from `vw_PowerBI_AI_Technical_Combos`)
- **Strategy 2**: ML classifier (Buy/Sell/Hold) with confidence % + RSI alignment → Grades A-D (from `vw_strategy2_trade_opportunities` for NSE, `ml_trading_predictions` for NASDAQ)
- Cross-strategy alignment occurs when both agree on direction

## Coding Patterns
- Agent factories: `create_*_agent() -> crewai.Agent` in `agents/*.py`
- Query dicts: `MARKET_INTEL_QUERIES`, `ML_ANALYST_QUERIES`, etc. in `config/sql_queries.py`
- LLM: `LLM(model=f"anthropic/{LLM_MODEL}", max_tokens=1500, temperature=0.2-0.3)`
- Tools inherit from `crewai.tools.BaseTool` with Pydantic `args_schema`

## Sibling Repositories (same database)
- `sqlserver_copilot` — NASDAQ ML training pipeline
- `sqlserver_copilot_nse` — NSE ML training pipeline
- `sqlserver_copilot_forex` — Forex ML training pipeline
- `sqlserver_mcp` — .NET 8 MCP Server (Microsoft MssqlMcp) with 7 tools: ListTables, DescribeTable, ReadData, CreateTable, DropTable, InsertData, UpdateData. Stdio transport. Use to explore DB schemas and verify query results during development.
- `streamlit-trading-dashboard` — Visualization, signal tracking, AI predictions
- `stockanalysis` — Data ingestion ETL (yfinance, Alpha Vantage)

## MCP Server for Development
Configure in `.vscode/mcp.json` to query stockdata_db directly from your AI IDE:
```json
"MSSQL MCP": {
    "type": "stdio",
    "command": "C:\\Users\\sreea\\OneDrive\\Desktop\\sqlserver_mcp\\SQL-AI-samples\\MssqlMcp\\dotnet\\MssqlMcp\\bin\\Debug\\net8.0\\MssqlMcp.exe",
    "env": {
        "CONNECTION_STRING": "Server=192.168.87.27\\MSSQLSERVER01;Database=stockdata_db;User Id=remote_user;Password=YourStrongPassword123!;TrustServerCertificate=True"
    }
}
```
Useful for: exploring table schemas before adding queries to `sql_queries.py`, verifying data freshness, checking view definitions.

## When Modifying SQL Queries
1. Add to the appropriate dict in `config/sql_queries.py`
2. Reference by key name in the agent's task description
3. The `PredefinedSQLQueryTool` will make it available to the agent
4. Test with `python main.py --test-sql`

## When Adding a New Agent
1. Create `agents/new_agent.py` with factory function
2. Add a query dict to `config/sql_queries.py`
3. Add agent + task in `crews/daily_briefing_crew.py`
4. Add 60s pause before new agent in the sequential pipeline
5. Add section to `templates/briefing_email.html`
