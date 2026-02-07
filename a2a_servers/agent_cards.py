"""
A2A Agent Cards - Discovery metadata for each specialist agent.
Each agent card describes the agent's capabilities so other agents
and clients can discover and communicate with them via A2A protocol.
"""

AGENT_CARDS = {
    "market_intel": {
        "name": "Market Intelligence Agent",
        "description": (
            "Analyzes latest price action, volume patterns, and market trends "
            "across NASDAQ 100 and NSE 500 markets. Provides market breadth, "
            "top movers, and overall sentiment assessment."
        ),
        "url": "http://localhost:5001",
        "capabilities": [
            "market_summary",
            "top_movers",
            "market_breadth",
            "volume_analysis",
        ],
        "input_modes": ["text"],
        "output_modes": ["text"],
    },
    "ml_analyst": {
        "name": "ML Model Analyst Agent",
        "description": (
            "Evaluates prediction accuracy and health of 3 ML models: "
            "Linear Regression, Gradient Boosting, and Random Forest. "
            "Provides model health scorecards, accuracy comparisons, "
            "and degradation alerts."
        ),
        "url": "http://localhost:5002",
        "capabilities": [
            "model_accuracy",
            "model_comparison",
            "degradation_detection",
            "accuracy_by_market",
        ],
        "input_modes": ["text"],
        "output_modes": ["text"],
    },
    "tech_signal": {
        "name": "Technical Signal Agent",
        "description": (
            "Identifies active buy/sell signals from MACD, RSI, Bollinger Bands, "
            "Stochastic, Fibonacci, SMA, and pattern analysis. Tracks historical "
            "signal outcomes at 7d, 14d, and 30d horizons."
        ),
        "url": "http://localhost:5003",
        "capabilities": [
            "active_signals",
            "signal_outcomes",
            "strongest_setups",
            "indicator_analysis",
        ],
        "input_modes": ["text"],
        "output_modes": ["text"],
    },
    "strategy_trade": {
        "name": "Strategy & Trade Agent",
        "description": (
            "Finds top trade opportunities by combining AI predictions with "
            "technical signals. Ranks opportunities by tier (TIER 1/2/3), "
            "provides entry/exit levels, risk/reward ratios, and warnings."
        ),
        "url": "http://localhost:5004",
        "capabilities": [
            "top_opportunities",
            "tier_analysis",
            "aligned_signals",
            "trade_management",
        ],
        "input_modes": ["text"],
        "output_modes": ["text"],
    },
    "forex": {
        "name": "Forex Analysis Agent",
        "description": (
            "Analyzes currency pair movements with focus on USD/INR. "
            "Provides latest rates, ML prediction signals, trend analysis "
            "against moving averages, and forex outlook."
        ),
        "url": "http://localhost:5005",
        "capabilities": [
            "forex_rates",
            "forex_predictions",
            "trend_analysis",
            "usd_inr_outlook",
        ],
        "input_modes": ["text"],
        "output_modes": ["text"],
    },
    "risk": {
        "name": "Risk Assessment Agent",
        "description": (
            "Evaluates overall risk posture across all markets. Identifies "
            "high-risk positions, conflicting signals, portfolio concentration, "
            "and provides family assets wealth summary."
        ),
        "url": "http://localhost:5006",
        "capabilities": [
            "risk_assessment",
            "conflicting_signals",
            "portfolio_risk",
            "wealth_summary",
        ],
        "input_modes": ["text"],
        "output_modes": ["text"],
    },
}
