# CLAUDE.md — Stock Data Agentic AI Platform

> **Master project context file for AI assistants (Claude, Copilot, Cursor).**
> Last updated: February 21, 2026

---

## 1. SYSTEM OVERVIEW

This is one of **7 interconnected repositories** that form an end-to-end **AI-powered stock trading analytics platform**. All repos share a single SQL Server database (`stockdata_db`) on `192.168.86.55\MSSQLSERVER01` (SQL Auth).

### Repository Map

| Layer | Repo | Location | Purpose |
|-------|------|----------|---------|
| **Data Ingestion** | `stockanalysis` | `C:\Users\sreea\OneDrive\Documents\stockanalysis` | ETL: fetches NSE 500, NASDAQ 100, Forex prices + fundamentals via yfinance/Alpha Vantage → SQL Server |
| **SQL Infrastructure** | `sqlserver_mcp` | `Desktop\sqlserver_mcp` | .NET 8 MCP Server (Microsoft MssqlMcp) — 7 tools (ListTables, DescribeTable, ReadData, CreateTable, DropTable, InsertData, UpdateData) via stdio transport for AI IDE ↔ SQL Server |
| **SQL Views + Dashboard** | `streamlit-trading-dashboard` | `Desktop\streamlit-trading-dashboard` | Creates 40+ technical indicator views, signal tracking tables, AI prediction history; 15-page Streamlit dashboard |
| **ML: NASDAQ** | `sqlserver_copilot` | ML Machine (`192.168.86.56`) | Gradient Boosting classifier → `ml_trading_predictions` (daily 6:00 AM, weekly retrain) |
| **ML: NSE** | `sqlserver_copilot_nse` | ML Machine (`192.168.86.56`) | 5-model ensemble → `ml_nse_trading_predictions` + regression (daily 9:30 AM, weekly Sun 2 AM) |
| **ML: Forex** | `sqlserver_copilot_forex` | ML Machine (`192.168.86.56`) | XGBoost/LightGBM/Stacking → `forex_ml_predictions` (daily 7:00 AM, weekly Sun 6 AM) |
| **Agentic AI** ⭐ | `stockdata_agenticai` | `Desktop\stockdata_agenticai` | **THIS REPO** — 7 CrewAI agents, daily email briefing, interactive chat, A2A HTTP API |

### Daily Execution Timeline (All times EST, Mon-Fri)

```
06:00 AM  sqlserver_copilot         → NASDAQ ML predictions → ml_trading_predictions
06:30 AM  sqlserver_copilot         → Data freshness check + conditional retrain
07:00 AM  sqlserver_copilot_forex   → Forex ML predictions → forex_ml_predictions
08:00 AM  stockdata_agenticai       → 8-agent briefing crew → HTML email
09:30 AM  sqlserver_copilot_nse     → NSE ML predictions → ml_nse_trading_predictions
06:00 PM  streamlit-dashboard       → AI price predictions → ai_prediction_history
07:00 PM  streamlit-dashboard       → Signal tracking → signal_tracking_history
```

### Machine Topology

| Machine | IP | Role | Repos Running |
|---------|-----|------|---------------|
| **Machine A** (SQL Server host) | `192.168.86.55` | Database server, ETL, dashboards, agentic AI | `stockanalysis`, `streamlit-trading-dashboard`, `stockdata_agenticai`, `sqlserver_mcp` |
| **Machine B** (ML Machine) | `192.168.86.56` | ML training & daily predictions | `sqlserver_copilot`, `sqlserver_copilot_nse`, `sqlserver_copilot_forex` |

All ML repos on Machine B connect to SQL Server on Machine A via SQL Auth (`remote_user`).

---

## 2. THIS REPO: stockdata_agenticai

### Purpose
A **read-only consumer** of the shared database. Runs 7 CrewAI agents that query SQL Server, analyze the data using Claude LLM, and compile an HTML email briefing sent daily at 8:00 AM. Also provides an interactive chat assistant and A2A HTTP API.

### Three Operating Modes

| Mode | Entry Point | Command |
|------|-------------|---------|
| **Daily Briefing** | `main.py` | `python main.py` |
| **Interactive Chat** | `chat_assistant.py` | `python chat_assistant.py` |
| **A2A HTTP API** | `a2a_servers/launch_all_agents.py` | `python -m a2a_servers.launch_all_agents` |

### File Map

```
stockdata_agenticai/
├── main.py                         # CLI entry point (--dry-run, --test-sql, --test-email)
├── chat_assistant.py               # Interactive chat (single mega-agent with all queries)
├── config/
│   ├── settings.py                 # .env loader → typed constants (18 env vars)
│   └── sql_queries.py              # 37 predefined SQL queries in 7 dictionaries
├── agents/
│   ├── market_intel_agent.py       # Agent 1: Market breadth, top movers
│   ├── ml_analyst_agent.py         # Agent 2: Model accuracy scorecards
│   ├── tech_signal_agent.py        # Agent 3: Active technical signals
│   ├── strategy_trade_agent.py     # Agent 4: TIER 1/2 trade opportunities
│   ├── forex_agent.py              # Agent 5: Forex rates + ML signals
│   ├── risk_agent.py               # Agent 6: Conflicting signals, portfolio risk
│   ├── cross_strategy_agent.py     # Agent 7: Dual-strategy alignment (NSE + NASDAQ)
│   ├── valuation_agent.py          # Agent 8: Fair value estimates (Graham, PEG, FWD, EPV)
│   └── report_compiler_agent.py    # UNUSED — replaced by Jinja2 compilation
├── crews/
│   └── daily_briefing_crew.py      # Master orchestrator (sequential, 60s pauses)
├── tools/
│   ├── sql_tool.py                 # PredefinedSQLQueryTool + SQLQueryTool (ad-hoc)
│   ├── email_tool.py               # SendEmailTool (Office 365 SMTP)
│   └── calculation_tools.py        # AccuracyCalc, PnLCalc, RiskRewardCalc
├── templates/
│   └── briefing_email.html         # Jinja2 HTML email template (8 sections)
├── a2a_servers/
│   ├── a2a_agent_server.py         # Flask HTTP server (1 per agent)
│   ├── agent_cards.py              # A2A discovery metadata (6 agents)
│   ├── a2a_client_example.py       # Demo client
│   └── launch_all_agents.py        # Spawns 6 servers on ports 5001-5006
├── sql/
│   └── create_performance_indexes.sql  # 13 covering indexes for query performance
├── run_briefing.bat                # Task Scheduler entry point
├── setup_scheduler.bat             # One-time scheduler setup
└── logs/run_log.txt                # Execution log (exit codes + timestamps)
```

---

## 3. AGENT REGISTRY

All agents follow the **factory pattern**: `create_*_agent() -> crewai.Agent`

| # | Agent | Role | LLM Temp | Tools | Query Dict | Key Tables/Views |
|---|-------|------|----------|-------|------------|------------------|
| 1 | Market Intel | Senior Market Analyst | 0.3 | PredefinedSQLQueryTool | `MARKET_INTEL_QUERIES` (4) | `nasdaq_100_hist_data`, `nse_500_hist_data` |
| 2 | ML Analyst | ML Performance Analyst | 0.2 | PredefinedSQLQueryTool, AccuracyCalc | `ML_ANALYST_QUERIES` (8) | `ai_prediction_history`, `ml_prediction_summary`, `ml_nse_predict_summary`, `forex_ml_predictions`, `ml_trading_predictions` |
| 3 | Tech Signal | CMT (Technical) | 0.2 | PredefinedSQLQueryTool | `TECH_SIGNAL_QUERIES` (4) | `vw_PowerBI_AI_Technical_Combos`, `signal_tracking_history` |
| 4 | Strategy Trade | Trading Strategy Manager | 0.3 | PredefinedSQLQueryTool, RiskRewardCalc | `STRATEGY_TRADE_QUERIES` (8) | `vw_PowerBI_AI_Technical_Combos`, `trade_log`, `ml_trading_predictions`, `ml_nse_trading_predictions` |
| 5 | Forex | Forex Specialist | 0.3 | PredefinedSQLQueryTool | `FOREX_QUERIES` (4) | `forex_hist_data`, `forex_ml_predictions` |
| 6 | Risk | FRM (Risk Manager) | 0.2 | PredefinedSQLQueryTool, PnLCalc | `RISK_QUERIES` (5) | `vw_strategy2_trade_opportunities`, `vw_PowerBI_AI_Technical_Combos`, `portfolio_tracker`, `trading_alerts`, `family_assets` |
| 7 | Cross-Strategy | Quantitative Strategist | 0.2 | PredefinedSQLQueryTool | `CROSS_STRATEGY_QUERIES` (4) | `vw_PowerBI_AI_Technical_Combos`, `vw_strategy2_trade_opportunities`, `ml_trading_predictions` |
| 8 | Fair Value | Fundamental Valuation Analyst | 0.2 | PredefinedSQLQueryTool | `VALUATION_QUERIES` (4) | `vw_fair_value_estimates`, `nasdaq_100_fundamentals`, `nse_500_fundamentals` |
| — | Report Compiler | (UNUSED) | 0.4 | SendEmailTool | — | — |

### Execution Pattern
Each agent runs as an independent mini-crew (`_run_single_agent()`) with 60-second pauses between them to respect the Anthropic 10K tokens/minute rate limit. Total runtime: ~8-12 minutes.

---

## 4. TWO-STRATEGY FRAMEWORK

### Strategy 1 (AI + Technical Combos)
- **Source**: `vw_PowerBI_AI_Technical_Combos` view
- **Method**: AI price prediction models (LR/GB/RF) combined with 6 technical indicator signals (MACD, RSI, BB, Stochastic, Fibonacci, Pattern)
- **Output**: TIER 1 ULTRA (76-93% win rate) / TIER 2 MODERATE classifications
- **Direction**: BULLISH / BEARISH

### Strategy 2 (ML Classifier + RSI)
- **Source**: `vw_strategy2_trade_opportunities` view (NSE), `ml_trading_predictions` (NASDAQ)
- **Method**: ML Buy/Sell classifier with confidence % + RSI category alignment
- **Output**: Trade grades A (HIGH CONVICTION SHORT) through D
- **Direction**: Buy / Sell with confidence percentage

### Cross-Strategy Logic
When both strategies agree on direction → **ALIGNED** (highest conviction). When they disagree → **CONFLICTING** (caution flag). Requires `ml_confidence_pct >= 55` and `signal_strength IN ('Strong', 'Moderate')`.

---

## 5. SQL QUERY CATALOG (41 queries)

### MARKET_INTEL_QUERIES (4)
| Query | Description |
|-------|-------------|
| `nasdaq_top_movers` | Top 5 NASDAQ movers by daily change % |
| `nse_top_movers` | Top 5 NSE movers by daily change % |
| `nasdaq_market_summary` | NASDAQ breadth: up/down/flat counts, avg change |
| `nse_market_summary` | NSE breadth: up/down/flat counts, avg change |

### ML_ANALYST_QUERIES (8)
| Query | Description |
|-------|-------------|
| `model_accuracy_last_7_days` | Strategy 2 model accuracy (direction_correct) by model, 7d window |
| `model_accuracy_last_30_days` | Same, 30d window |
| `model_accuracy_by_market` | Accuracy breakdown by market (NASDAQ/NSE) |
| `recent_predictions_summary` | Latest predictions with actual vs predicted |
| `strategy1_nasdaq_ml_summary` | NASDAQ ML classifier daily stats from summary table |
| `strategy1_nse_ml_summary` | NSE ML classifier daily stats from summary table |
| `strategy1_forex_ml_summary` | Forex ML signal counts and confidence |
| `strategy1_forex_ml_accuracy` | Forex 1-day direction accuracy |

### TECH_SIGNAL_QUERIES (4)
| Query | Description |
|-------|-------------|
| `active_signals_today` | Today's active BULLISH/BEARISH signals with tier/combo |
| `signal_outcomes_7d` | 7-day signal outcome tracking (win/loss) |
| `signal_outcomes_14d` | 14-day signal outcome tracking |
| `strongest_signals_recent` | Recent strongest signals by strength score |

### STRATEGY_TRADE_QUERIES (8)
| Query | Description |
|-------|-------------|
| `top_tier1_opportunities` | Top 15 TIER 1 trades across markets |
| `top_tier2_opportunities` | Top 15 TIER 2 trades across markets |
| `tier_summary_today` | TIER 1/2 count by market with avg AI prediction |
| `open_trades` | Open positions from trade_log |
| `nasdaq_tier1_today` | Top 10 NASDAQ TIER 1 signals |
| `nse_tier1_today` | Top 10 NSE TIER 1 signals |
| `strategy1_nasdaq_top_signals` | Top 10 NASDAQ ML classifier Buy/Sell signals |
| `strategy1_nse_top_signals` | Top 10 NSE ML classifier Buy/Sell signals |

### FOREX_QUERIES (4)
| Query | Description |
|-------|-------------|
| `forex_latest_rates` | Current rates + daily changes + moving averages |
| `forex_ml_predictions_latest` | ML Buy/Sell/Hold signals with confidence |
| `forex_ml_signal_summary` | Aggregate Buy vs Sell vs Hold counts |
| `forex_weekly_trend` | 7-day trend with week open/close/high/low |

### RISK_QUERIES (5)
| Query | Description |
|-------|-------------|
| `portfolio_positions` | Open portfolio positions |
| `active_alerts` | Active trading alert configurations |
| `high_risk_positions` | Stocks with conflicting ML + tech signals |
| `conflicting_signals` | Cross-strategy direction disagreements |
| `family_assets_summary` | Family asset totals by type |

### CROSS_STRATEGY_QUERIES (4)
| Query | Description |
|-------|-------------|
| `common_stocks_both_strategies` | NSE stocks in both strategies with alignment status |
| `common_stocks_summary` | NSE aligned vs conflicting counts |
| `common_stocks_nasdaq` | NASDAQ stocks in both strategies (joins AI+Tech with ml_trading_predictions) |
| `common_stocks_nasdaq_summary` | NASDAQ aligned vs conflicting counts |

### VALUATION_QUERIES (4)
| Query | Description |
|-------|-----------|
| `nasdaq_top20_undervalued` | Top 20 NASDAQ stocks by margin of safety (composite fair value vs implied price) |
| `nse_top20_undervalued` | Top 20 NSE stocks by margin of safety |
| `valuation_summary_by_market` | Valuation verdict distribution (undervalued/fair/overvalued) per market |
| `sector_valuation_heatmap` | Sector-level valuation breakdown with avg margin of safety |

---

## 6. DATABASE SCHEMA

### Shared SQL Server
- **Server**: `192.168.86.55\MSSQLSERVER01` (Machine A LAN IP)
- **Database**: `stockdata_db`
- **Auth**: SQL Auth (`SQL_USERNAME=remote_user`, `SQL_TRUSTED_CONNECTION=no`)
- **Driver**: ODBC Driver 17 for SQL Server
- **Note**: Machine A (SQL Server host) can also use `localhost\MSSQLSERVER01` with Windows Auth for local access
- **ML Machine**: `192.168.86.56` — runs `sqlserver_copilot`, `sqlserver_copilot_nse`, `sqlserver_copilot_forex` (daily/weekly ML training jobs)

### Tables (29+)

#### Market Data (populated by `stockanalysis` repo)
| Table | ~Rows | Key Columns |
|-------|-------|-------------|
| `nasdaq_100_hist_data` | 127,889 | ticker, trading_date, open/high/low/close_price (VARCHAR), volume |
| `nse_500_hist_data` | 509,799 | Same schema |
| `forex_hist_data` | — | symbol, currency_from/to, OHLC (DECIMAL), daily_change, 50d/200d avg |
| `nasdaq_top100` | 100 | ticker (PK), company_name, sector, industry, process_flag |
| `nse_500` | 500 | ticker (PK), company_name, sector, industry, process_flag |
| `forex_master` | 10 | symbol, currency_from/to, is_active |
| `nasdaq_100_fundamentals` | — | ticker, fetch_date, 37 fundamental metrics |
| `nse_500_fundamentals` | — | Same schema |
| `market_context_daily` | — | trading_date (PK), VIX/India VIX close+change, S&P 500/NASDAQ/NIFTY 50 close+return, DXY close+return, US 10Y yield+change, 11 US sector ETF returns, 5 India sector index returns |

#### ML Predictions (populated by `sqlserver_copilot*` repos)
| Table | ~Rows | Written By | Key Columns |
|-------|-------|-----------|-------------|
| `ml_trading_predictions` | 5,041 | `sqlserver_copilot` | ticker, trading_date, predicted_signal, confidence_percentage, signal_strength, RSI, buy/sell_probability |
| `ml_nse_trading_predictions` | 28,647 | `sqlserver_copilot_nse` | Same + model_name, sector, market_cap_category, high_confidence |
| `forex_ml_predictions` | 290 | `sqlserver_copilot_forex` | currency_pair, predicted_signal, signal_confidence, prob_buy/sell/hold, model_name, model_version |
| `ai_prediction_history` | 45,135 | `streamlit-dashboard` | model_name (LR/GB/RF), predicted/actual_price, direction_correct, absolute/percentage_error |
| `ml_prediction_summary` | — | `sqlserver_copilot` | Daily aggregate: buy/sell counts, avg confidence, trend counts |
| `ml_nse_predict_summary` | — | `sqlserver_copilot_nse` | Daily aggregate + model_accuracy, success_rate_1d/5d/10d |
| `ml_technical_indicators` | — | `sqlserver_copilot` | NASDAQ SMA/EMA/MACD/RSI/volatility snapshots |
| `ml_nse_technical_indicators` | — | `sqlserver_copilot_nse` | NSE technical indicator snapshots |

#### Signal Tracking (populated by `streamlit-dashboard` repo)
| Table | Written By | Key Columns |
|-------|-----------|-------------|
| `signal_tracking_history` | `streamlit-dashboard` | market, ticker, signal_date, signal_type, signal_strength, result_7d/14d/30d, actual_change |
| `daily_signals_history` | `streamlit-dashboard` | — |

#### Strategy/Trading
| Table | Purpose |
|-------|---------|
| `trade_log` | Manual/automated trade entries (entry/exit price, P&L) |
| `trading_alerts` | Configurable alert thresholds |
| `prediction_watchlist` | Tickers selected for AI predictions |
| `stock_notes` | Per-stock journal entries |

#### Personal/Portfolio
| Table | Purpose |
|-------|---------|
| `portfolio_tracker` | Open/closed positions with buy/sell prices |
| `family_assets` | Family asset inventory |

### Views (3 critical ones used by this repo)
| View | Source | Purpose |
|------|--------|--------|
| `vw_PowerBI_AI_Technical_Combos` | Joins `ai_prediction_history` + `signal_tracking_history` | TIER 1/2 trade signals with AI prediction % + 6 technical indicators |
| `vw_strategy2_trade_opportunities` | Joins ML classifier + tech alignment | Trade grades A-D with opportunity_score, recommended_action |
| `vw_fair_value_estimates` | Joins `nasdaq_100_fundamentals` / `nse_500_fundamentals` + master tables | 4-model fair value (Graham, PEG, Forward Earnings, EPV) with composite value + margin of safety |

### Additional Views (created by `streamlit-dashboard` and `stockanalysis`)
- **Per-market indicator views** (NSE/NASDAQ/Forex): `{market}_RSI_calculation`, `{market}_macd`, `{market}_bollingerband`, `{market}_ema_sma_view`, `{market}_atr`, `{market}_stochastic`, `{market}_fibonacci`, `{market}_support_resistance`, `{market}_patterns`
- **Signal views**: `{market}_rsi_signals`, `{market}_macd_signals`, `{market}_bb_signals`, `{market}_sma_signals`, `{market}_atr_spikes`
- **Crossover views**: `vw_crossover_signals_NSE_500`, `vw_crossover_signals_NASDAQ_100`, `vw_crossover_signals_Forex`
- **Fundamental screening**: `vw_value_stocks_screen`, `vw_quality_stocks_screen`, `vw_growth_stocks_screen`, `vw_dividend_stocks_screen`, `vw_fundamental_scoring`
- **Performance views**: `vw_signal_performance_summary`, `vw_model_performance_summary`, `vw_recent_prediction_accuracy`

---

## 7. ENVIRONMENT VARIABLES

All loaded from `.env` via `python-dotenv` in `config/settings.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | — | Claude API key |
| `LLM_MODEL` | `claude-sonnet-4-20250514` | Model identifier |
| `SQL_SERVER` | `192.168.86.55\MSSQLSERVER01` | SQL Server host (Machine A LAN IP) |
| `SQL_DATABASE` | `stockdata_db` | Database name |
| `SQL_DRIVER` | `{ODBC Driver 17 for SQL Server}` | ODBC driver |
| `SQL_USERNAME` | `remote_user` | SQL Auth username |
| `SQL_PASSWORD` | *(in .env)* | SQL Auth password |
| `SQL_TRUSTED_CONNECTION` | `no` | SQL Auth (not Windows Auth) |
| `SMTP_SERVER` | `smtp.office365.com` | Email server |
| `SMTP_PORT` | `587` | STARTTLS port |
| `SMTP_USERNAME` | — | Email login |
| `SMTP_PASSWORD` | — | Email password |
| `EMAIL_FROM_NAME` | — | Sender display name |
| `EMAIL_FROM` | — | Sender address |
| `EMAIL_TO` | — | Recipient(s) |
| `AGENT_MAX_ITER` | `5` | Max agent iterations |
| `AGENT_VERBOSE` | `true` | Verbose logging |
| `AGENT_MAX_RPM` | `4` | Max LLM requests/minute |

---

## 8. CODING CONVENTIONS

### Agent Factory Pattern
```python
def create_*_agent() -> Agent:
    tool = PredefinedSQLQueryTool(name=..., query_set=DOMAIN_QUERIES)
    llm = LLM(model=f"anthropic/{LLM_MODEL}", max_tokens=1500, temperature=0.2-0.3)
    return Agent(role=..., goal=..., backstory=..., tools=[tool], llm=llm,
                 verbose=AGENT_VERBOSE, max_iter=AGENT_MAX_ITER,
                 max_rpm=AGENT_MAX_RPM, allow_delegation=False, inject_date=True)
```

### SQL Query Organization
- Queries live in `config/sql_queries.py` as raw SQL strings in domain-specific dicts
- Agents access them via `PredefinedSQLQueryTool` scoped to their dict
- Chat assistant merges all dicts with domain prefixes (`market_`, `ml_`, etc.)

### Mini-Crew Execution
```python
def _run_single_agent(agent, task_description, expected_output) -> str:
    task = Task(description=..., expected_output=..., agent=agent)
    mini_crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, memory=False)
    return mini_crew.kickoff().raw
```

### Key Rules
- This repo is **read-only** against the database — never writes/inserts
- All price columns in `nasdaq_100_hist_data` and `nse_500_hist_data` are **VARCHAR** — cast to FLOAT in queries
- `report_compiler_agent.py` is **unused** — email is compiled via Jinja2 directly
- Cross-Strategy Agent is **NOT** exposed via A2A (only 6 of 7 agents are)
- Chat assistant has **no memory** — each question is stateless

---

## 9. EXTERNAL DEPENDENCIES

| Package | Version | Purpose |
|---------|---------|---------|
| `crewai` | ≥0.108.0 | Multi-agent orchestration |
| `crewai-tools` | ≥0.37.0 | Tool base classes |
| `anthropic` | ≥0.42.0 | Claude SDK |
| `pyodbc` | ≥5.1.0 | SQL Server connectivity |
| `python-dotenv` | ≥1.0.0 | .env loading |
| `jinja2` | ≥3.1.0 | HTML email templates |
| `python-a2a[anthropic]` | ≥0.5.0 | Google A2A protocol |
| `flask` | ≥2.0.0 | A2A HTTP servers |

---

## 10. KNOWN ISSUES & PLANNED WORK

### Active Issues
- Price columns as VARCHAR in NSE/NASDAQ hist tables → requires CAST in every query
- No model drift detection or automated degradation alerts
- Cross-strategy confidence thresholds (55%, 60%, 70%) are hardcoded, not calibrated
- Chat assistant is stateless (no conversation memory)
- Forex excluded from Strategy 2 due to regression model underperformance

### Planned Phases (from plan doc)
- **Phase 4**: Trade Journal + Model Monitor agents
- **Phase 5**: Portfolio Risk + Backtesting agents
- **Phase 6**: News Sentiment agent + enhanced A2A

### Improvement Opportunities
- P0: Confidence calibration, model degradation alerts
- P1: Ensemble weighting in cross-strategy, multi-horizon accuracy tracking
- P2: Drift detection, sector-stratified evaluation, Hold class for classifiers
- P3: Feature importance tracking, model versioning/registry

---

## 11. MCP SERVER FOR DEVELOPMENT

The `sqlserver_mcp` repo provides an MCP server that AI IDEs can use to query the shared database directly during development. This is useful for exploring table schemas, verifying query results, and testing SQL before adding it to `config/sql_queries.py`.

### 7 MCP Tools Available
| Tool | Purpose | Read-Only |
|------|---------|----------|
| ListTables | List all tables from INFORMATION_SCHEMA | Yes |
| DescribeTable | Get columns, types, constraints for a table | Yes |
| ReadData | Execute SQL queries | Yes |
| CreateTable | Create new tables | No |
| DropTable | Drop tables | No (destructive!) |
| InsertData | Insert rows | No |
| UpdateData | Update rows | No |

### VS Code Configuration
Add to `.vscode/mcp.json` or VS Code settings:
```json
"MSSQL MCP": {
    "type": "stdio",
    "command": "C:\\Users\\sreea\\OneDrive\\Desktop\\sqlserver_mcp\\SQL-AI-samples\\MssqlMcp\\dotnet\\MssqlMcp\\bin\\Debug\\net8.0\\MssqlMcp.exe",
    "env": {
        "CONNECTION_STRING": "Server=192.168.86.55\\MSSQLSERVER01;Database=stockdata_db;User Id=remote_user;Password=YourStrongPassword123!;TrustServerCertificate=True"
    }
}
```

### Development Use Cases for This Repo
- Explore table schemas before writing new SQL queries for `sql_queries.py`
- Verify query output format before agents parse it
- Check data freshness (latest trading_date) before debugging agent issues
- Investigate new views/tables created by sibling repos
