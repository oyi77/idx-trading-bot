"""Alert engine — create, check, and trigger price alerts for IDX stocks.

Alert types:
  - Price: symbol > 4600 (crosses above/below)
  - Percentage: symbol > +5% (from entry price)
  - Technical: symbol oversold (RSI < 30)

Storage: SQLite via models.Alert
Checker: periodic loop triggered by cron job
"""
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Alert, User
from src.engine.technical import TechnicalEngine
from yfinance import Ticker


class AlertEngine:
    """Manage alert lifecycle: create, check, trigger, notify."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_alert(
        self, user_id: int, symbol: str,
        condition: str, value: float,
        alert_type: str = "price",
    ) -> Optional[Alert]:
        """Create a new alert. Returns None if limit reached."""
        # Check limit
        from src.models import Subscription, SubscriptionTier
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await self.db.execute(stmt)
        sub = result.scalar_one_or_none()
        if not sub:
            return None

        max_alerts = SubscriptionTier.LIMITS.get(sub.tier, {}).get("alerts", 5)

        # Count active alerts
        count_stmt = select(Alert).where(
            Alert.user_id == user_id,
            Alert.is_active == True,
            Alert.is_triggered == False,
        )
        count_result = await self.db.execute(count_stmt)
        active_count = len(count_result.scalars().all())

        if active_count >= max_alerts:
            return None

        alert = Alert(
            user_id=user_id,
            symbol=symbol.upper(),
            condition=condition,
            value=value,
            alert_type=alert_type,
            created_at=datetime.utcnow(),
            is_active=True,
            is_triggered=False,
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def cancel_alert(self, alert_id: int, user_id: int) -> bool:
        """Deactivate an alert."""
        stmt = select(Alert).where(
            Alert.id == alert_id,
            Alert.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        alert = result.scalar_one_or_none()
        if not alert:
            return False
        alert.is_active = False
        await self.db.commit()
        return True

    async def get_user_alerts(self, user_id: int) -> List[Alert]:
        """Get all active alerts for a user."""
        stmt = select(Alert).where(
            Alert.user_id == user_id,
            Alert.is_active == True,
        ).order_by(Alert.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def check_all_alerts(self) -> List[Tuple[Alert, User, str]]:
        """Check all active alerts against current market prices.
        Returns list of (alert, user, message) for triggered alerts.
        """
        stmt = select(Alert).where(
            Alert.is_active == True,
            Alert.is_triggered == False,
        )
        result = await self.db.execute(stmt)
        alerts = list(result.scalars().all())

        triggered = []
        # Group by symbol to minimize API calls
        symbols = set(a.symbol for a in alerts)

        # Fetch prices for all symbols
        prices: dict[str, float] = {}
        for sym in symbols:
            try:
                ticker = Ticker(f"{sym}.JK")
                hist = ticker.history(period="5d")
                if not hist.empty:
                    prices[sym] = hist["Close"].iloc[-1]
            except Exception:
                pass

        for alert in alerts:
            current_price = prices.get(alert.symbol)
            if current_price is None:
                continue

            # Check conditions
            triggered_flag = False
            if alert.condition == ">":
                triggered_flag = current_price > alert.value
            elif alert.condition == "<":
                triggered_flag = current_price < alert.value
            elif alert.condition == ">=":
                triggered_flag = current_price >= alert.value
            elif alert.condition == "<=":
                triggered_flag = current_price <= alert.value
            elif alert.condition == "=":
                triggered_flag = abs(current_price - alert.value) / alert.value < 0.01  # within 1%

            if not triggered_flag:
                continue

            # Mark as triggered
            alert.is_triggered = True
            alert.triggered_at = datetime.utcnow()

            # Get user info
            user_stmt = select(User).where(User.id == alert.user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            direction = "naik" if current_price > alert.value else "turun"
            emoji = "🟢" if current_price > alert.value else "🔴"
            msg = (
                f"{emoji} *ALERT TRIGGERED*: {alert.symbol}\n"
                f"Harga sekarang: Rp{current_price:,.0f}\n"
                f"Kondisi: {alert.symbol} {alert.condition} {alert.value:,.0f}\n"
                f"Harga {direction} {abs(current_price - alert.value):,.0f} poin"
            )
            triggered.append((alert, user, msg))

        if triggered:
            await self.db.commit()

        return triggered

    async def get_active_count(self, user_id: int) -> int:
        """Count active alerts for a user."""
        stmt = select(Alert).where(
            Alert.user_id == user_id,
            Alert.is_active == True,
            Alert.is_triggered == False,
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
