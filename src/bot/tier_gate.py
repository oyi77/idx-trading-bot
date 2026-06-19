"""Tier-gating system — maps commands to subscription tiers.

Tier Mapping:
  Free     = Basic analysis, 5 alerts, no real-time, no AI insight
  Pro      = Full analysis + screener + alerts + real-time + AI
  Premium  = Bandar + Sentiment + Sector + Event + Report + Jejak + Auto
  Lifetime = Premium for life
  WhiteLabel = Full access + branding
"""

import logging
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)

# ── Command → Minimum Tier Map ─────────────────────────────────
COMMAND_TIERS = {
    # ── Core (Free) ──
    "start":         "free",
    "help":          "free",
    "panduan":       "free",
    "pricing":       "free",
    "faq":           "free",

    # ── Analysis (Free with limits, Pro unlimited) ──
    "analisa":       "free",
    "stats":         "free",

    # ── Pro Features ──
    "screener_momentum":    "pro",
    "screener_reversal":    "pro",
    "screener_breakout":    "pro",
    "screener_smartmoney":  "pro",
    "signal_swing":        "pro",
    "signal_scalp":        "pro",
    "sinyal_swing":        "pro",
    "sinyal_scalp":        "pro",
    "autopilot_status":    "lifetime",
    "autopilot_daily":     "lifetime",
    "autopilot_backtest":  "lifetime",
    "plan":                 "pro",
    "myplans":              "pro",
    "alert":                "pro",
    "myalerts":             "pro",
    "portfolio":            "pro",
    "watchlist":            "pro",
    "journal":              "pro",

    # ── Premium Features ──
    "jejak":                "premium",
    "performance":          "premium",
    "leaderboard":          "premium",
    "leaderboard_top":      "premium",
    "leaderboard_streak":   "premium",
    "points":               "premium",
    "bandarmology":         "premium",
    "event":                "premium",
    "report":               "premium",

    # ── Market (mixed) ──
    "premarket":            "pro",
    "briefing":             "pro",
    "ihsg":                 "free",
    "sector":               "pro",
    "calendar":             "pro",
    "news":                 "free",
    "trending":             "free",
    "breadth":              "pro",

    # ── Account ──
    "upgrade":              "free",
    "handle_message":       "free",
}

# ── Tier hierarchy for comparison ──────────────────────────────
TIER_LEVELS = {
    "free":      0,
    "pro":       1,
    "premium":   2,
    "lifetime":  3,
    "whitelabel": 4,
    "admin":     5,
}


def get_tier_level(tier: str) -> int:
    """Convert tier string to numeric level."""
    return TIER_LEVELS.get(tier, 0)


def get_user_tier_sync(telegram_id: int) -> str:
    """Get user's current tier from database (sync, fast read)."""
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import sessionmaker
        from src.models import User, Base

        sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
        engine = create_engine(sync_url)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user and hasattr(user, 'subscription') and user.subscription:
                return user.subscription.tier or "free"
        engine.dispose()
    except Exception as e:
        logger.warning(f"get_user_tier_sync failed for {telegram_id}: {e}")
    return "free"


def check_tier(telegram_id: int, command: str) -> tuple:
    """
    Check if user has access to a command.
    Returns: (has_access, user_tier, upgrade_message)
    """
    required = COMMAND_TIERS.get(command, "free")
    user_tier = get_user_tier_sync(telegram_id)
    
    user_level = get_tier_level(user_tier)
    required_level = get_tier_level(required)
    
    if user_level >= required_level:
        return True, user_tier, None
    
    # Build upgrade message
    if required == "pro":
        msg = (
            "🔒 *Fitur Pro*\n\n"
            "Upgrade ke Pro buat akses:\n"
            "• Screener 693 saham (4 kategori)\n"
            "• Trading plan + AI analisa\n"
            "• 50 alert real-time\n"
            "• Portfolio tracking\n\n"
            "💰 Cuma *Rp79.900/bulan*\n\n"
            "Ketik /upgrade"
        )
    elif required == "premium":
        msg = (
            "🔒 *Fitur Premium*\n\n"
            "Upgrade ke Premium buat akses:\n"
            "• Deteksi bandar + asing real-time\n"
            "• Market Sentiment\n"
            "• Forecast sektor + event classifier\n"
            "• Auto-report mingguan\n"
            "• Jejak Cuan + performa\n\n"
            "💰 Cuma *Rp149.000/bulan*\n\n"
            "Ketik /upgrade"
        )
    else:
        msg = "🔒 Fitur ini nggak tersedia di tier kamu."
    
    return False, user_tier, msg


def get_tier_badge(tier: str) -> str:
    """Get emoji badge for tier display."""
    badges = {
        "free": "🆓",
        "pro": "💎",
        "premium": "👑",
        "lifetime": "🌟",
        "whitelabel": "🏢",
        "admin": "⚡",
    }
    return badges.get(tier, "🆓")


def get_tier_limits(tier: str) -> dict:
    """Get limits for a tier."""
    from src.models import SubscriptionTier
    return SubscriptionTier.LIMITS.get(tier, SubscriptionTier.LIMITS["free"])
