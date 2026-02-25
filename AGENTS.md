# AGENTS.md — Agent Architecture Reference

## Overview
This repo runs **8 CrewAI agents** sequentially to produce a daily HTML market briefing email.
All agents are **read-only** — they query SQL Server via predefined SQL and return LLM-analyzed text.

## Architecture

```
main.py → DailyBriefingCrew.run()
  ├─ Agent 1: Market Intel       (4 queries, 200 words)
  ├─ 60s pause (rate limit)
  ├─ Agent 2: ML Analyst         (8 queries, 250 words)
  ├─ 60s pause
  ├─ Agent 3: Tech Signal        (4 queries, 250 words)
  ├─ 60s pause
  ├─ Agent 4: Strategy & Trade   (8 queries, 250 words)
  ├─ 60s pause
  ├─ Agent 5: Forex Tech & ML    (9 queries, 350 words)
  ├─ 60s pause
  ├─ Agent 6: Risk               (5 queries, 200 words)
  ├─ 60s pause
  ├─ Agent 7: Cross-Strategy     (4 queries, 350 words)
  ├─ 60s pause
  ├─ Agent 8: Fair Value          (4 queries, 350 words)
  └─ Jinja2 HTML compilation → SendEmailTool
```

## Agent Details

### Agent 1 — Market Intel Agent
- **File**: `agents/market_intel_agent.py`
- **Role**: Senior Market Analyst
- **Temperature**: 0.3
- **Tools**: PredefinedSQLQueryTool (MARKET_INTEL_QUERIES)
- **Queries**: `nasdaq_top_movers`, `nse_top_movers`, `nasdaq_market_summary`, `nse_market_summary`
- **Output**: Market breadth + top 5 movers per market

### Agent 2 — ML Analyst Agent
- **File**: `agents/ml_analyst_agent.py`
- **Role**: ML Model Performance Analyst
- **Temperature**: 0.2
- **Tools**: PredefinedSQLQueryTool (ML_ANALYST_QUERIES), AccuracyCalculatorTool
- **Queries**: 8 queries covering model accuracy (7d/30d/market), prediction summaries, classifier stats
- **Output**: Model scorecard with HEALTHY/WARNING/CRITICAL status per model

### Agent 3 — Tech Signal Agent
- **File**: `agents/tech_signal_agent.py`
- **Role**: CMT (Chartered Market Technician)
- **Temperature**: 0.2
- **Tools**: PredefinedSQLQueryTool (TECH_SIGNAL_QUERIES)
- **Queries**: `active_signals_today`, `signal_outcomes_7d`, `signal_outcomes_14d`, `strongest_signals_recent`
- **Output**: Active signals with historical win rates

### Agent 4 — Strategy & Trade Agent
- **File**: `agents/strategy_trade_agent.py`
- **Role**: Trading Strategy Manager
- **Temperature**: 0.3
- **Tools**: PredefinedSQLQueryTool (STRATEGY_TRADE_QUERIES), RiskRewardCalculatorTool
- **Queries**: 8 queries covering TIER 1/2 opportunities, open trades, market ML signals
- **Output**: Top 5 high-conviction trades with entry/exit/stop levels

### Agent 5 — Forex Technical & ML Agent
- **File**: `agents/forex_agent.py`
- **Role**: Forex Technical Analyst & ML Specialist
- **Temperature**: 0.3
- **Tools**: PredefinedSQLQueryTool (FOREX_QUERIES)
- **Queries**: `forex_latest_rates`, `forex_ml_predictions_latest`, `forex_ml_signal_summary`, `forex_weekly_trend`, `forex_technical_signals`, `forex_crossover_signals`, `forex_support_resistance`, `forex_pattern_signals`, `forex_technical_vs_ml`
- **Output**: Technical indicator dashboard (RSI, MACD, BB, Stochastic), support/resistance levels, crossover & pattern signals, ML confirmation, technical-vs-ML agreement status
- **Philosophy**: Forex follows patterns/technicals more reliably than equities — technicals are PRIMARY, ML is CONFIRMATION

### Agent 6 — Risk Agent
- **File**: `agents/risk_agent.py`
- **Role**: FRM (Financial Risk Manager)
- **Temperature**: 0.2
- **Tools**: PredefinedSQLQueryTool (RISK_QUERIES), PnLCalculatorTool
- **Queries**: `portfolio_positions`, `active_alerts`, `high_risk_positions`, `conflicting_signals`, `family_assets_summary`
- **Output**: Portfolio risk assessment, conflicting signals, exposure analysis

### Agent 7 — Cross-Strategy Agent
- **File**: `agents/cross_strategy_agent.py`
- **Role**: Quantitative Strategist
- **Temperature**: 0.2
- **Tools**: PredefinedSQLQueryTool (CROSS_STRATEGY_QUERIES)
- **Queries**: `common_stocks_both_strategies` + `common_stocks_summary` (NSE), `common_stocks_nasdaq` + `common_stocks_nasdaq_summary` (NASDAQ)
- **Output**: Aligned/conflicting stock analysis for both NSE 500 and NASDAQ 100

### Agent 8 — Fair Value / Valuation Agent
- **File**: `agents/valuation_agent.py`
- **Role**: Fundamental Valuation Analyst
- **Temperature**: 0.2
- **Tools**: PredefinedSQLQueryTool (VALUATION_QUERIES)
- **Queries**: `nasdaq_top20_undervalued`, `nse_top20_undervalued`, `valuation_summary_by_market`, `sector_valuation_heatmap`
- **Output**: Top 20 undervalued stocks per market with composite fair value, margin of safety %, and valuation verdict
- **View Dependency**: `vw_fair_value_estimates` (4 models: Graham Number, PEG, Forward Earnings, EPV)

## Tool Registry

| Tool | Class | File | Purpose |
|------|-------|------|---------|
| PredefinedSQLQueryTool | BaseTool (CrewAI) | `tools/sql_tool.py` | Runs queries from a fixed set (scoped per agent) |
| SQLQueryTool | BaseTool (CrewAI) | `tools/sql_tool.py` | Runs ad-hoc SQL (chat mode only) |
| SendEmailTool | BaseTool (CrewAI) | `tools/email_tool.py` | Sends HTML email via Office 365 SMTP |
| AccuracyCalculatorTool | BaseTool (CrewAI) | `tools/calculation_tools.py` | Computes model accuracy from input data |
| PnLCalculatorTool | BaseTool (CrewAI) | `tools/calculation_tools.py` | Calculates P&L for positions |
| RiskRewardCalculatorTool | BaseTool (CrewAI) | `tools/calculation_tools.py` | Computes risk/reward ratios |

## A2A HTTP API (Agent-to-Agent)

6 of the 7 agents are exposed as independent HTTP servers:

| Agent | Port | Endpoint |
|-------|------|----------|
| Market Intel | 5001 | `POST /` |
| ML Analyst | 5002 | `POST /` |
| Tech Signal | 5003 | `POST /` |
| Strategy Trade | 5004 | `POST /` |
| Forex | 5005 | `POST /` |
| Risk | 5006 | `POST /` |

Cross-Strategy and Valuation agents are **not** exposed via A2A.

## Limitations
- Agents have **no memory** — each run is stateless
- **No delegation** (`allow_delegation=False` on all agents)
- **Max iterations**: configurable via `AGENT_MAX_ITER` (default 5)
- **Rate limit**: 60s sleep between agents, `max_rpm=4` per agent
- All agents are **read-only** against the database
