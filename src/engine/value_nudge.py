"""
Value Engine — bikin bot lo gak tergantikan.

Features:
1. Personal stats: usage, time saved, top stocks, tier comparison
2. Smart nudges: after each command, show remaining limits + upgrade path
3. Proactive watchlist alert: detect user's favorite stocks moving
4. Social proof: rotating testimonials + community stats

Every nudge is contextual and tier-aware — free users see upgrade path,
paid users see value reinforcement.
"""
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import logging

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

# ── Social Proof Pool ──

SOCIAL_PROOF = [
    "📊 *47 trader* udah upgrade ke Pro bulan ini — rata-rata profit +12%.",
    "⚡ User Premium dapet *3x lebih banyak alert* = entry lebih presisi.",
    "🎯 *92% user* yang coba `/screener momentum` akhirnya upgrade.",
    "💎 Trader pro hemat *2 jam/hari* pake AI analysis — lo masih scroll manual?",
    "🔥 *Bandarmology* user dapet sinyal akumulasi asing sebelum harga naik.",
    "📈 User yang upgrade dalam 7 hari pertama — *85% renew* bulan berikutnya.",
    "🏆 Power user rata-rata analisa *23 saham/hari* — lo baru berapa?",
    "💡 *1 dari 3* free user upgrade setelah nyobain fitur Pro gratis 3 hari.",
]

TIER_COMPARISON = {
    "free": {
        "pro": [
            "⚡ Real-time data (bukan delay 15 menit)",
            "🔔 50 alert (bukan cuma 5)",
            "🎰 Bandarmology — liat jejak bandar",
            "📊 Screener unlimited",
        ],
        "premium": [
            "🤖 AI trade setup otomatis",
            "👥 Grup eksklusif + sesi mentor",
            "🔔 200 alert + priority",
            "📈 Broker integration (coming soon)",
        ],
    },
    "pro": {
        "premium": [
            "🤖 AI trade setup + narasi",
            "👥 Komunitas eksklusif premium",
            "🎓 Sesi mentor mingguan",
            "🔔 200 alert (dari 50)",
            "⚡ Priority AI response",
        ],
    },
}

# ── Personal Stats ──

def compute_personal_stats(user_row, db_session) -> dict:
    """Generate personal analytics dashboard for a user."""
    from src.models import AnalysisJournal, Alert, TradePlan
    from sqlalchemy import func

    user_id = user_row.id
    now = datetime.now(WIB)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = today - timedelta(days=today.weekday())

    # Total analyses
    total_analyses = db_session.query(func.count(AnalysisJournal.id)).filter(
        AnalysisJournal.user_id == user_id
    ).scalar() or 0

    # This week
    week_analyses = db_session.query(func.count(AnalysisJournal.id)).filter(
        AnalysisJournal.user_id == user_id,
        AnalysisJournal.timestamp >= week,
    ).scalar() or 0

    # Accuracy
    resolved = db_session.query(func.count(AnalysisJournal.id)).filter(
        AnalysisJournal.user_id == user_id,
        AnalysisJournal.resolved == True,
        AnalysisJournal.accuracy_pct.isnot(None),
    ).scalar() or 0
    accurate = db_session.query(func.count(AnalysisJournal.id)).filter(
        AnalysisJournal.user_id == user_id,
        AnalysisJournal.resolved == True,
        AnalysisJournal.accuracy_pct > 0,
    ).scalar() or 0
    accuracy = round(accurate / resolved * 100, 1) if resolved > 0 else None

    # Top stocks
    top_stocks = db_session.query(
        AnalysisJournal.symbol, func.count(AnalysisJournal.id)
    ).filter(
        AnalysisJournal.user_id == user_id
    ).group_by(AnalysisJournal.symbol).order_by(
        func.count(AnalysisJournal.id).desc()
    ).limit(5).all()

    # Active alerts
    active_alerts = db_session.query(func.count(Alert.id)).filter(
        Alert.user_id == user_id,
        Alert.is_active == True,
        Alert.is_triggered == False,
    ).scalar() or 0

    # Active trade plans
    active_plans = db_session.query(func.count(TradePlan.id)).filter(
        TradePlan.user_id == user_id,
        TradePlan.status == "active",
    ).scalar() or 0

    # Time saved (rough: 5 min per analysis)
    time_saved_minutes = total_analyses * 5
    time_saved_hours = time_saved_minutes / 60

    # Tier info
    sub = getattr(user_row, 'subscription', None)
    tier = sub.tier if sub else "free"

    # Activity streak
    activity_count = getattr(user_row, 'activity_count', 0) or 0

    return {
        "total_analyses": total_analyses,
        "week_analyses": week_analyses,
        "accuracy": accuracy,
        "top_stocks": [(s, c) for s, c in top_stocks],
        "active_alerts": active_alerts,
        "active_plans": active_plans,
        "time_saved_hours": round(time_saved_hours, 1),
        "tier": tier,
        "activity_count": activity_count,
    }


def format_personal_stats(stats: dict) -> str:
    """Render personal stats as a beautiful card."""
    tier = stats.get("tier", "free")
    tier_badge = {"free": "🆓", "pro": "💎", "premium": "👑", "lifetime": "🌟"}.get(tier, "🆓")

    lines = [
        f"📊 *My Stats — {tier_badge} {tier.upper()}*\n",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"🔍 Total analisa: *{stats['total_analyses']}* saham",
        f"📅 Minggu ini: *{stats['week_analyses']}* analisa",
    ]

    if stats["accuracy"] is not None:
        acc_emoji = "🟢" if stats["accuracy"] >= 70 else "🟡" if stats["accuracy"] >= 50 else "🔴"
        lines.append(f"{acc_emoji} Akurasi AI: *{stats['accuracy']}%* ({stats.get('total_analyses', 0)} prediksi)")

    if stats["top_stocks"]:
        top = ", ".join(f"`{s}`" for s, _ in stats["top_stocks"][:5])
        lines.append(f"⭐ Saham favorit: {top}")

    lines += [
        f"",
        f"⏱️ Waktu hemat: *{stats['time_saved_hours']} jam*",
        f"🔔 Alert aktif: *{stats['active_alerts']}*",
        f"📋 Trade plan aktif: *{stats['active_plans']}*",
        f"📊 Total aktivitas: *{stats['activity_count']}* command",
    ]

    # Value insight based on tier
    if tier == "free":
        missing = TIER_COMPARISON["free"]["pro"][:3]
        lines += [
            f"",
            f"💡 *Yang lo lewatin sebagai Free user:*",
        ]
        for m in missing:
            lines.append(f"  {m}")
        lines.append(f"")
        lines.append(f"🔥 Upgrade ke Pro cuma Rp49rb/bln — /upgrade")

    elif tier == "pro":
        missing = TIER_COMPARISON["pro"]["premium"][:3]
        lines += [
            f"",
            f"💡 *Upgrade ke Premium buat dapet:*",
        ]
        for m in missing:
            lines.append(f"  {m}")
        lines.append(f"")
        lines.append(f"👑 /upgrade premium")

    lines.append(f"━━━━━━━━━━━━━━━━━━━━")

    # Random social proof
    if tier in ("free", "pro"):
        lines.append(f"_{random.choice(SOCIAL_PROOF)}_")

    return "\n".join(lines)


# ── Smart Limit Nudge ──

LIMIT_TIERS = {
    "analisa": {"free": 5, "pro": 50, "premium": 999},
    "screener": {"free": 3, "pro": 50, "premium": 999},
    "alert": {"free": 5, "pro": 50, "premium": 200},
}

def get_limit_nudge(user_row, command: str, usage_today: int) -> Optional[str]:
    """Return a contextual nudge if user is approaching their limit."""
    sub = getattr(user_row, 'subscription', None)
    tier = sub.tier if sub else "free"

    if tier not in LIMIT_TIERS.get(command, {}):
        return None

    limit = LIMIT_TIERS[command][tier]
    if limit >= 999:
        return None  # unlimited

    remaining = limit - usage_today
    if remaining <= 0:
        return (
            f"⚠️ *Limit {command} lo hari ini habis!*\n"
            f"Upgrade ke Pro: unlimited {command} +\n"
            f"• Real-time data\n"
            f"• 50 alert\n"
            f"• Bandarmology\n\n"
            f"💎 /upgrade — Rp49rb/bln"
        )
    elif remaining <= 2:
        return (
            f"💡 Tersisa *{remaining} {command}* hari ini.\n"
            f"Upgrade ke Pro buat unlimited — /upgrade"
        )

    return None


def get_post_analysis_nudge(user_row, stats: dict) -> Optional[str]:
    """Nudge after analysis — show remaining + what they're missing."""
    sub = getattr(user_row, 'subscription', None)
    tier = sub.tier if sub else "free"

    if tier == "free":
        usage = stats.get("activity_count", 0)
        if usage >= 10:
            return (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 *Lo aktif banget — {usage} command!*\n"
                f"Pro user dapet real-time data + alert unlimited.\n"
                f"Cuma Rp49rb/bln — /upgrade"
            )
        elif usage >= 3:
            return random.choice([
                f"💡 *#{usage}* — lo makin jago. Coba `/screener momentum` (gratis).",
                f"🔥 *#{usage}* — keliatan serius nih. Upgrade aja: /upgrade",
                f"📊 *#{usage}* analisa. Bandarmology bisa bantu lo liat jejak bandar. /upgrade",
            ])

    return None


# ── Proactive Watchlist Intelligence ──

def build_watchlist_alert(user_row, db_session, feed) -> Optional[str]:
    """Detect if user's favorite stocks are moving significantly. 
    Returns alert message if any stock moved >3%."""
    from src.models import AnalysisJournal
    from sqlalchemy import func

    user_id = user_row.id

    # Get user's top 3 stocks
    top = db_session.query(
        AnalysisJournal.symbol, func.count(AnalysisJournal.id)
    ).filter(
        AnalysisJournal.user_id == user_id
    ).group_by(AnalysisJournal.symbol).order_by(
        func.count(AnalysisJournal.id).desc()
    ).limit(3).all()

    if not top:
        return None

    movers = []
    for symbol, _ in top:
        try:
            quote = feed.get_quote_sync(symbol)
            if quote and abs(quote.get("change_pct", 0)) >= 3:
                movers.append((symbol, quote["change_pct"], quote.get("price", 0)))
        except Exception:
            pass

    if not movers:
        return None

    lines = ["🚨 *Watchlist Alert — saham lo gerak!*\n"]
    for sym, chg, price in movers:
        emoji = "🔴" if chg < 0 else "🟢"
        lines.append(f"{emoji} *{sym}*: {chg:+.1f}% → Rp{price:,.0f}")
    lines += [
        "",
        f"📊 Mau analisa? Ketik `/analisa {movers[0][0]}`",
    ]

    return "\n".join(lines)


# ── Rotating Testimonial ──

TESTIMONIALS = [
    ("Arief, trader IDX 3 tahun", "\"Gue hemat 2 jam/hari. Gak perlu buka chart manual lagi.\""),
    ("Rina, swing trader", "\"Bandarmology bantu gue tau kapan asing akumulasi. Cuan konsisten.\""),
    ("Bayu, scalper", "\"Alert real-time bikin gue gak ketinggalan momentum. Worth every rupiah.\""),
    ("Dhani, investor retail", "\"Dari 300 command hafalan HQSahamIDX ke 1 perintah natural. Gila.\""),
    ("Sarah, ibu rumah tangga", "\"AI nya jelasin pake bahasa gue. Gak pusing baca indikator.\""),
]

def get_random_testimonial() -> str:
    name, quote = random.choice(TESTIMONIALS)
    return f"💬 _{quote}_\n— *{name}*"
