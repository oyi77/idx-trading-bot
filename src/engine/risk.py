"""Risk manager — position sizing and risk controls.

Calculates:
  - Lot size based on risk percentage (1-2% of capital per trade)
  - Safe entry/stop-loss levels
  - Risk/reward ratio validation (min 1:2)
  - Portfolio limits
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class PositionSizing:
    symbol: str
    capital: float  # Total trading capital (Rp)
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    risk_percent: float = 1.0  # % of capital to risk per trade
    direction: str = "long"

    # Calculated
    risk_per_share: float = 0.0
    shares: int = 0
    lots: int = 0  # IDX: 1 lot = 100 shares
    risk_amount: float = 0.0
    risk_reward_ratio: float = 0.0
    potential_profit: float = 0.0
    position_value: float = 0.0


class RiskManager:
    """Calculate position sizing and validate trades."""

    SHARES_PER_LOT = 100  # IDX standard
    MAX_RISK_PERCENT = 2.0
    MIN_RR_RATIO = 1.5  # Minimum risk/reward ratio

    def calculate_position(
        self,
        symbol: str,
        capital: float,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float] = None,
        risk_percent: float = 1.0,
        direction: str = "long",
    ) -> PositionSizing:
        """Calculate optimal position size."""
        risk_percent = min(risk_percent, self.MAX_RISK_PERCENT)

        if direction == "long":
            risk_per_share = entry_price - stop_loss
            potential_profit = (take_profit - entry_price) if take_profit else 0
        else:
            risk_per_share = stop_loss - entry_price
            potential_profit = (entry_price - take_profit) if take_profit else 0

        risk_per_share = abs(risk_per_share)
        potential_profit = abs(potential_profit)
        risk_amount = capital * (risk_percent / 100)

        # Calculate shares (must be multiple of lot size)
        raw_shares = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        lots = max(raw_shares // self.SHARES_PER_LOT, 1)
        shares = lots * self.SHARES_PER_LOT

        # Recalculate actual risk
        actual_risk = shares * risk_per_share
        position_value = shares * entry_price
        rr_ratio = round(potential_profit / risk_per_share, 2) if risk_per_share > 0 else 0

        return PositionSizing(
            symbol=symbol,
            capital=capital,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_percent=risk_percent,
            direction=direction,
            risk_per_share=risk_per_share,
            shares=shares,
            lots=lots,
            risk_amount=actual_risk,
            risk_reward_ratio=rr_ratio,
            potential_profit=potential_profit * shares,
            position_value=position_value,
        )

    def validate_trade(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float] = None,
        direction: str = "long",
    ) -> list[str]:
        """Validate a trade setup. Returns list of warnings."""
        warnings = []

        if direction == "long":
            if stop_loss >= entry_price:
                warnings.append("⚠️ Stop loss harus di bawah entry price untuk posisi long")
            if take_profit and take_profit <= entry_price:
                warnings.append("⚠️ Take profit harus di atas entry price untuk posisi long")
        else:  # short
            if stop_loss <= entry_price:
                warnings.append("⚠️ Stop loss harus di atas entry price untuk posisi short")
            if take_profit and take_profit >= entry_price:
                warnings.append("⚠️ Take profit harus di bawah entry price untuk posisi short")

        if take_profit:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            if risk > 0 and reward / risk < self.MIN_RR_RATIO:
                warnings.append(
                    f"⚠️ Risk/Reward ratio {reward/risk:.1f}x < {self.MIN_RR_RATIO}x minimum"
                )

        return warnings

    def format_sizing(self, sizing: PositionSizing) -> str:
        """Format position sizing result for Telegram."""
        capital_b = sizing.capital / 1_000_000_000
        rr_color = "🟢" if sizing.risk_reward_ratio >= 2 else ("🟡" if sizing.risk_reward_ratio >= 1 else "🔴")
        risk_pct = (sizing.risk_amount / sizing.capital) * 100

        return (
            f"📐 *Position Sizing*\n"
            f"Modal: Rp{capital_b:,.2f}B\n"
            f"Risiko: {risk_pct:.1f}% dari modal (Rp{sizing.risk_amount:,.0f})\n"
            f"Lot: {sizing.lots} lot ({sizing.shares} shares)\n"
            f"Entry: Rp{sizing.entry_price:,.0f} (nilai: Rp{sizing.position_value:,.0f})\n"
            f"SL: Rp{sizing.stop_loss:,.0f} | TP: Rp{sizing.take_profit:,.0f}\n"
            f"{rr_color} R/R: {sizing.risk_reward_ratio}x"
        )
