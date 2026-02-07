# Stock Data Agentic AI Platform

A true multi-agent AI system built with **CrewAI** and **Google A2A Protocol** that analyzes stock market data, ML predictions, technical signals, forex, and portfolio risk -- then delivers insights via daily email briefings, an interactive chat assistant, or A2A HTTP API endpoints.

## Architecture

```
Master Orchestrator (CrewAI Crew - Sequential Process)
├── Agent 1: Market Intelligence Agent     (NASDAQ 100 + NSE 500 price/volume analysis)
├── Agent 2: ML Model Analyst Agent        (Model accuracy & health monitoring)
├── Agent 3: Technical Signal Agent        (Buy/sell signals & 7d/14d/30d outcomes)
├── Agent 4: Strategy & Trade Agent        (Top TIER 1/2 opportunities, risk/reward)
├── Agent 5: Forex Analysis Agent          (Currency pair analysis, USD/INR focus)
├── Agent 6: Risk Assessment Agent         (Portfolio risk, conflicting signals, warnings)
└── Agent 7: Report Compiler Agent         (HTML email compilation & Office 365 delivery)
```

### Three Modes of Operation

1. **Daily Briefing** (`main.py`) - Automated morning email with full market analysis
2. **Interactive Chat** (`chat_assistant.py`) - Natural language Q&A against all 29 tables
3. **A2A HTTP API** (`a2a_servers/`) - Each agent as a standalone HTTP service

### Agent Communication Patterns

- **Intra-Crew**: Sequential pipeline where each agent's output becomes context for the next
- **Agents as Tools**: Any agent can call another agent as a tool (CrewAI native)
- **A2A Protocol**: Each agent exposed as an HTTP endpoint via Google A2A standard

## Tech Stack

- **Framework**: CrewAI 1.9+ (multi-agent orchestration)
- **LLM**: Anthropic Claude (via native SDK)
- **A2A Protocol**: Google Agent-to-Agent (python-a2a)
- **Database**: SQL Server (via pyodbc, 29 tables, 700K+ records)
- **Email**: Office 365 SMTP
- **Scheduling**: Windows Task Scheduler

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` with your Anthropic API key and email credentials:

```bash
# Required: Set your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Required for email: Office 365 credentials
SMTP_USERNAME=your-email@domain.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@domain.com
EMAIL_TO=your-email@domain.com
```

SQL Server is pre-configured for local `stockdata_db` with Windows Authentication.

### 3. Test Connectivity

```bash
python main.py --test-sql       # Test SQL Server (should show 29 tables)
python main.py --test-email     # Test email delivery
```

### 4. Run Daily Briefing

```bash
python main.py                  # Full run: analyze + email
python main.py --dry-run        # Analyze only, no email sent
```

### 5. Interactive Chat

```bash
python chat_assistant.py                                    # Interactive mode
python chat_assistant.py --query "Top TIER 1 signals today" # Single query
```

### 6. A2A Agent Servers

```bash
# Launch all 6 agent servers (ports 5001-5006)
python a2a_servers/launch_all_agents.py

# Or launch individual agents
python a2a_servers/a2a_agent_server.py --agent market_intel --port 5001
python a2a_servers/a2a_agent_server.py --agent ml_analyst --port 5002

# Test with the example client
python a2a_servers/a2a_client_example.py
```

### 7. Schedule Automated Daily Briefing

Run as Administrator:
```bash
setup_scheduler.bat    # Creates Windows Task Scheduler job for weekdays 8:00 AM
```

## Project Structure

```
stockdata_agenticai/
├── config/
│   ├── settings.py               # Central configuration (from .env)
│   └── sql_queries.py            # 25 SQL queries organized by agent domain
├── tools/
│   ├── sql_tool.py               # SQL Server query tool (pyodbc)
│   ├── email_tool.py             # Office 365 SMTP email tool
│   └── calculation_tools.py      # Financial calculators (accuracy, P&L, R:R)
├── agents/
│   ├── market_intel_agent.py     # Agent 1: Market Intelligence
│   ├── ml_analyst_agent.py       # Agent 2: ML Model Analyst
│   ├── tech_signal_agent.py      # Agent 3: Technical Signal
│   ├── strategy_trade_agent.py   # Agent 4: Strategy & Trade
│   ├── forex_agent.py            # Agent 5: Forex Analysis
│   ├── risk_agent.py             # Agent 6: Risk Assessment
│   └── report_compiler_agent.py  # Agent 7: Report Compiler
├── crews/
│   └── daily_briefing_crew.py    # Orchestrator: assembles Crew
├── a2a_servers/
│   ├── agent_cards.py            # A2A discovery metadata
│   ├── a2a_agent_server.py       # Flask server per agent
│   ├── launch_all_agents.py      # Launch all 6 servers
│   └── a2a_client_example.py     # Example A2A client
├── templates/
│   └── briefing_email.html       # HTML email template
├── chat_assistant.py             # Interactive chat assistant
├── main.py                       # Daily briefing entry point
├── run_briefing.bat              # Runner for Task Scheduler
├── setup_scheduler.bat           # One-time scheduler setup
├── requirements.txt
└── .env.example
```

## SQL Server Tables (29 tables)

| Category | Tables | Records |
|----------|--------|---------|
| NASDAQ Data | nasdaq_100_hist_data, nasdaq_100_fundamentals, nasdaq_top100 | 128K+ |
| NSE Data | nse_500_hist_data, nse_500_fundamentals, nse_500 | 513K+ |
| ML Predictions | ai_prediction_history, ml_trading_predictions, ml_technical_indicators, ml_prediction_summary | 83K+ |
| NSE ML | ml_nse_trading_predictions, ml_nse_technical_indicators, ml_nse_predict_summary | 57K+ |
| Technical Signals | signal_tracking_history, daily_signals_history | 20K+ |
| Strategy | strategy1_tracking, trade_log, trading_alerts, prediction_watchlist | 1K+ |
| Forex | forex_hist_data, forex_ml_predictions, forex_daily_summary, forex_master, forex_model_performance, forex_prediction_features | 3.5K+ |
| Personal | portfolio_tracker, family_assets, stock_notes, bad_tickers | 400+ |
