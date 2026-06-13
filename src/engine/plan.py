"""Trading plan engine — execute, track, and evaluate trading plans.

Features:
  - Create plans with entry, SL, TP
  - Auto-evaluate: check if price hit SL or TP
  - Periodic report for active plans
  - Win/loss tracking
  - Risk/reward ratio calculator
"""
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import TradePlan, User


class TradePlanEngine:
    """Manage trading plan lifecycle."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_plan(
        self, user_id: int, symbol: str,
        entry_price: float, stop_loss: float,
        take_profit: Optional[float] = None,
        direction: str = "long",
        notes: str = "",
    ) -> Optional[TradePlan]:
        """Create a new trading plan."""
        plan = TradePlan(
            user_id=user_id,
            symbol=symbol.upper(),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            direction=direction,
            status="active",
            notes=notes,
            auto_report=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def cancel_plan(self, plan_id: int, user_id: int) -> bool:
        """Cancel a trading plan."""
        stmt = select(TradePlan).where(
            TradePlan.id == plan_id,
            TradePlan.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        plan = result.scalar_one_or_none()
        if not plan:
            return False

        plan.status = "cancelled"
        plan.updated_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def get_user_plans(self, user_id: int, status: str = "active") -> List[TradePlan]:
        """Get plans for a user by status."""
        stmt = select(TradePlan).where(
            TradePlan.user_id == user_id,
            TradePlan.status == status,
        ).order_by(TradePlan.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def evaluate_plans(self) -> List[Tuple[TradePlan, User, str]]:
        """Check all active plans against current prices.
        Returns list of (plan, user, message) for plans that hit SL or TP.
        """
        stmt = select(TradePlan).where(TradePlan.status == "active")
        result = await self.db.execute(stmt)
        plans = list(result.scalars().all())

        updates = []
        symbols = set(p.symbol for p in plans)

        # Batch fetch prices
        from yfinance import Ticker
        prices: dict[str, float] = {}
        for sym in symbols:
            try:
                ticker = Ticker(f"{sym}.JK")
                hist = ticker.history(period="5d")
                if not hist.empty:
                    prices[sym] = hist["Close"].iloc[-1]
            except Exception:
                pass

        for plan in plans:
            current_price = prices.get(plan.symbol)
            if current_price is None:
                continue

            new_status = None
            if plan.direction == "long":
                if plan.stop_loss and current_price <= plan.stop_loss:
                    new_status = "hit_sl"
                elif plan.take_profit and current_price >= plan.take_profit:
                    new_status = "hit_tp"
            else:  # short
                if plan.stop_loss and current_price >= plan.stop_loss:
                    new_status = "hit_sl"
                elif plan.take_profit and current_price <= plan.take_profit:
                    new_status = "hit_tp"

            if not new_status:
                continue

            plan.status = new_status
            plan.updated_at = datetime.utcnow()

            # Get user
            user_stmt = select(User).where(User.id == plan.user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            loss = abs(current_price - plan.entry_price) * 100  # in Rupiah per lot (assuming 100 shares)
            is_win = "TP" if new_status == "hit_tp" else "SL"
            emoji = "🟢" if is_win == "TP" else "🔴"

            msg = (
                f"{emoji} *TRADING PLAN {is_win}* — {plan.symbol}\n"
                f"Entry: Rp{plan.entry_price:,.0f}\n"
                f"{'TP' if is_win == 'TP' else 'SL'}: Rp{current_price:,.0f}\n"
                f"P/L: Rp{abs(current_price - plan.entry_price):,.0f} per saham\n"
                f"R/R: {plan.risk_reward}x\n"
                f"Notes: {plan.notes or '-'}"
            )
            updates.append((plan, user, msg))

        if updates:
            await self.db.commit()

        return updates

    async def get_performance(self, user_id: int) -> dict:
        """Get win/loss stats for a user."""
        stmt_wins = select(func.count(TradePlan.id)).where(
            TradePlan.user_id == user_id,
            TradePlan.status == "hit_tp",
        )
        stmt_losses = select(func.count(TradePlan.id)).where(
            TradePlan.user_id == user_id,
            TradePlan.status == "hit_sl",
        )
        stmt_active = select(func.count(TradePlan.id)).where(
            TradePlan.user_id == user_id,
            TradePlan.status == "active",
        )
        wins = (await self.db.execute(stmt_wins)).scalar() or 0
        losses = (await self.db.execute(stmt_losses)).scalar() or 0
        active = (await self.db.execute(stmt_active)).scalar() or 0

        total = wins + losses
        return {
            "wins": wins,
            "losses": losses,
            "active": active,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "total_trades": total,
        }
