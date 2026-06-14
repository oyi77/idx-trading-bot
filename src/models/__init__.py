"""Database models for user management, subscriptions, trade plans, alerts."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeMeta, declarative_base, relationship, sessionmaker

from src.config import settings

Base: DeclarativeMeta = declarative_base()


# ── User ──

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=True)
    username = Column(String(100))
    full_name = Column(String(200))
    language = Column(String(10), default="id")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    activity_count = Column(Integer, default=0)  # total commands used
    followup_stage = Column(Integer, default=0)  # 0=no followup yet, 1-3=stage
    last_followup_at = Column(DateTime, nullable=True)  # anti-spam
    followup_segment = Column(String(20), default="new")  # new, active_free, sleeping, power_free
    onboarding_stage = Column(Integer, default=0)  # 0=none, 1-3=onboarding drip stages
    last_watchlist_alert_at = Column(DateTime, nullable=True)  # anti-spam: watchlist alert 24h cooldown
    is_active = Column(Boolean, default=True)

    # Relationships
    subscription = relationship("Subscription", uselist=False, back_populates="user")
    trade_plans = relationship("TradePlan", back_populates="user")
    alerts = relationship("Alert", back_populates="user")


# ── Subscription ──

class SubscriptionTier:
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"
    LIFETIME = "lifetime"
    WHITELABEL = "whitelabel"

    LIMITS = {
        FREE: {"screens_per_day": 5, "alerts": 5, "realtime": False},
        PRO: {"screens_per_day": 100, "alerts": 50, "realtime": True},
        PREMIUM: {"screens_per_day": 9999, "alerts": 200, "realtime": True},
        LIFETIME: {"screens_per_day": 9999, "alerts": 200, "realtime": True},
        WHITELABEL: {"screens_per_day": 9999, "alerts": 9999, "realtime": True},
    }

    PRICES = {
        PRO: 49000,
        PREMIUM: 149000,
        LIFETIME: 1999000,
        WHITELABEL: (5_000_000, 500_000),  # setup, monthly
    }


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    tier = Column(String(20), default=SubscriptionTier.FREE)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True)
    payment_provider = Column(String(50))  # midtrans, manual
    payment_status = Column(String(20))  # active, expired, pending

    user = relationship("User", back_populates="subscription")

    @property
    def is_pro(self) -> bool:
        return self.tier in (SubscriptionTier.PRO, SubscriptionTier.PREMIUM,
                            SubscriptionTier.LIFETIME, SubscriptionTier.WHITELABEL)

    @property
    def limits(self) -> dict:
        return SubscriptionTier.LIMITS.get(self.tier, SubscriptionTier.LIMITS[SubscriptionTier.FREE])


# ── Trade Plan ──

class TradePlan(Base):
    __tablename__ = "trade_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    direction = Column(String(10), default="long")  # long / short
    status = Column(String(20), default="active")  # active, hit_sl, hit_tp, cancelled
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    auto_report = Column(Boolean, default=True)
    source_message_id = Column(Integer, nullable=True)  # Telegram message_id from analisa response
    source_chat_id = Column(Integer, nullable=True)  # Telegram chat_id where analisa was sent

    user = relationship("User", back_populates="trade_plans")

    @property
    def risk_reward(self) -> float:
        if self.stop_loss and self.entry_price:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.take_profit - self.entry_price) if self.take_profit else 0
            return round(reward / risk, 2) if risk > 0 else 0
        return 0


# ── Alert ──

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    condition = Column(String(10))  # >, <, =, >=, <=
    value = Column(Float)
    is_triggered = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="alerts")


# ── Analysis Journal (AI Learning Loop) ──

class AnalysisJournal(Base):
    """Records every AI analysis for accuracy tracking & learning."""
    __tablename__ = "analysis_journal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String(32), unique=True, nullable=False)
    user_id = Column(ForeignKey("users.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    price_at_analysis = Column(Float)
    signal = Column(String(10))  # BUY / WATCH / PASS
    score = Column(Integer)
    ai_insight = Column(Text, default="")
    key_indicators = Column(Text, default="{}")  # JSON
    bias = Column(String(16), default="NEUTRAL")  # BULLISH / BEARISH / NEUTRAL
    experiment_tag = Column(String(32), default="v1")

    # Resolution (filled by cron later)
    resolved = Column(Boolean, default=False)
    actual_price = Column(Float, nullable=True)
    accuracy_pct = Column(Float, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 or NULL
    user_feedback_text = Column(Text, nullable=True)
    feedback_at = Column(DateTime, nullable=True)


# ── Screener Activity Log ──

class ScreenerLog(Base):
    """Records every screener run for dashboard stats."""
    __tablename__ = "screener_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    category = Column(String(20), nullable=False)  # momentum, reversal, breakout, smartmoney
    total_scanned = Column(Integer, default=0)
    total_hits = Column(Integer, default=0)
    hits_json = Column(Text, default="[]")  # JSON array of top hits {symbol, score, strategy}
    timestamp = Column(DateTime, default=datetime.utcnow)


# ── Database Setup ──

def get_engine():
    if settings.database_url.startswith("sqlite"):
        return create_async_engine(settings.database_url, echo=settings.debug)
    return create_async_engine(settings.database_url, echo=settings.debug)


def create_tables():
    """Sync table creation for setup script."""
    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()
