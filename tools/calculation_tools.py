"""
Calculation and statistics helper tools for agents.
Provides common financial calculations that agents can use.
"""

from crewai.tools import BaseTool
from pydantic import Field, BaseModel
from typing import Type


class AccuracyCalcInput(BaseModel):
    """Input for accuracy calculation."""
    correct: int = Field(description="Number of correct predictions.")
    total: int = Field(description="Total number of predictions.")


class AccuracyCalculatorTool(BaseTool):
    """Calculates prediction accuracy percentage."""
    name: str = "accuracy_calculator"
    description: str = (
        "Calculate prediction accuracy percentage. "
        "Provide the number of correct predictions and total predictions."
    )
    args_schema: Type[BaseModel] = AccuracyCalcInput

    def _run(self, correct: int, total: int) -> str:
        if total == 0:
            return "Cannot calculate accuracy: total is 0."
        accuracy = (correct / total) * 100
        return f"Accuracy: {accuracy:.2f}% ({correct}/{total})"


class PnLCalcInput(BaseModel):
    """Input for P&L calculation."""
    entry_price: float = Field(description="Entry/buy price.")
    current_price: float = Field(description="Current/exit price.")
    quantity: int = Field(description="Number of shares.")


class PnLCalculatorTool(BaseTool):
    """Calculates profit/loss for a position."""
    name: str = "pnl_calculator"
    description: str = (
        "Calculate profit/loss for a stock position. "
        "Provide entry price, current price, and quantity."
    )
    args_schema: Type[BaseModel] = PnLCalcInput

    def _run(self, entry_price: float, current_price: float, quantity: int) -> str:
        pnl = (current_price - entry_price) * quantity
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        return (
            f"P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%) | "
            f"Entry: ${entry_price:.2f} | Current: ${current_price:.2f} | "
            f"Qty: {quantity}"
        )


class RiskRewardCalcInput(BaseModel):
    """Input for risk/reward calculation."""
    entry_price: float = Field(description="Entry price.")
    stop_loss: float = Field(description="Stop loss price.")
    take_profit: float = Field(description="Take profit/target price.")


class RiskRewardCalculatorTool(BaseTool):
    """Calculates risk/reward ratio for a trade."""
    name: str = "risk_reward_calculator"
    description: str = (
        "Calculate risk/reward ratio for a trade setup. "
        "Provide entry price, stop loss, and take profit levels."
    )
    args_schema: Type[BaseModel] = RiskRewardCalcInput

    def _run(
        self, entry_price: float, stop_loss: float, take_profit: float
    ) -> str:
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        if risk == 0:
            return "Risk is 0 -- cannot calculate ratio."
        ratio = reward / risk
        return (
            f"Risk/Reward Ratio: 1:{ratio:.2f} | "
            f"Risk: ${risk:.2f} | Reward: ${reward:.2f} | "
            f"Entry: ${entry_price:.2f} | SL: ${stop_loss:.2f} | "
            f"TP: ${take_profit:.2f}"
        )
