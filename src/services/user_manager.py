"""User management service — tiers, limits, auth."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models import Subscription, SubscriptionTier, User


class UserManager:
    """Handle user lifecycle: register, upgrade, tier checks."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_or_create_user(self, telegram_id: int, username: str = "", full_name: str = "") -> User:
        """Find user by telegram_id or create new."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.last_active = datetime.utcnow()
            user.username = username or user.username
        else:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                last_active=datetime.utcnow(),
            )
            self.db.add(user)
            await self.db.flush()

            # Create free subscription
            sub = Subscription(user_id=user.id, tier=SubscriptionTier.FREE)
            self.db.add(sub)

        await self.db.commit()
        return user

    async def get_user(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def can_screen(self, user_id: int) -> bool:
        """Check if user has daily screen quota remaining."""
        # TODO: implement screen count tracking
        return True

    async def can_set_alert(self, user_id: int) -> bool:
        """Check if user can set more alerts."""
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await self.db.execute(stmt)
        sub = result.scalar_one_or_none()
        if not sub:
            return False
        max_alerts = SubscriptionTier.LIMITS.get(sub.tier, {}).get("alerts", 5)
        # TODO: count current active alerts
        return True

    def format_tier_info(self, tier: str) -> str:
        """Format tier benefits for display."""
        limits = SubscriptionTier.LIMITS.get(tier, SubscriptionTier.LIMITS[SubscriptionTier.FREE])
        price = SubscriptionTier.PRICES.get(tier, "Gratis")
        return (
            f"*{tier.upper()}*\n"
            f"💰 Harga: Rp{price:,}\n" if isinstance(price, int) else f"💰 Harga: {price}\n"
            f"📊 Screener: {limits['screens_per_day']}/hari\n"
            f"🔔 Alert: {limits['alerts']}\n"
            f"⚡ Real-time: {'✅' if limits['realtime'] else '❌ (15 menit delay)'}"
        )

    async def upgrade_tier(self, telegram_id: int, target_tier: str, amount_paid: int = 0) -> tuple:
        """Upgrade user subscription tier.

        Returns (success: bool, message: str).
        """
        from datetime import datetime, timezone, timedelta
        WIB = timezone(timedelta(hours=7))

        if target_tier not in SubscriptionTier.PRICES:
            return False, f"Tier tidak valid: {target_tier}"

        user = await self.get_user(telegram_id)
        if not user:
            return False, "User tidak ditemukan"

        stmt = select(Subscription).where(Subscription.user_id == user.id)
        result = await self.db.execute(stmt)
        sub = result.scalar_one_or_none()

        if not sub:
            sub = Subscription(user_id=user.id, tier=target_tier)
            self.db.add(sub)
        else:
            sub.tier = target_tier

        if target_tier == "lifetime":
            sub.expires_at = None
        elif target_tier != "whitelabel":
            sub.expires_at = datetime.now(WIB) + timedelta(days=30)

        sub.can_expire = target_tier not in ("lifetime", "whitelabel")
        sub.amount_paid = (sub.amount_paid or 0) + amount_paid
        sub.last_payment_at = datetime.now(WIB)

        await self.db.commit()

        tier_label = {"pro": "Pro", "premium": "Premium", "lifetime": "Lifetime", "whitelabel": "White-label"}
        return True, f"✅ Upgrade ke *{tier_label.get(target_tier, target_tier)}* berhasil!"
