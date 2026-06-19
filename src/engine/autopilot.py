"""Autopilot Engine — Autonomous marketing, follow-up, and self-improvement.

Runs as a scheduled background task (via APScheduler or cron).

Daily Tasks (07:00 WIB, before market open):
  1. Generate daily market map
  2. Generate swing + scalp signals
  3. Post to channel/group
  4. Run follow-up sweep (sleeping users, churned users, etc.)

Weekly Tasks (Sunday 08:00 WIB):
  1. Run backtest on both strategies
  2. Generate weekly report
  3. Apply optimization suggestions
  4. Post weekly summary to channel
  5. Generate marketing content (win rate showcase)

Continuous:
  - Track signal accuracy in journal
  - Update learning engine with results
  - Monitor win rate drift
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

AUTOSAVE_DIR = Path("data/autopilot")


@dataclass
class AutopilotStatus:
    """Current autopilot state."""
    last_daily_run: Optional[str] = None
    last_weekly_backtest: Optional[str] = None
    last_followup_sweep: Optional[str] = None
    last_marketing_post: Optional[str] = None
    current_win_rate_swing: float = 0.0
    current_win_rate_scalp: float = 0.0
    total_signals_posted: int = 0
    total_followups_sent: int = 0
    total_marketing_posts: int = 0


def load_status() -> AutopilotStatus:
    """Load autopilot status from disk."""
    status_file = AUTOSAVE_DIR / "status.json"
    if not status_file.exists():
        return AutopilotStatus()
    try:
        with open(status_file) as f:
            data = json.load(f)
        return AutopilotStatus(**data)
    except Exception:
        return AutopilotStatus()


def save_status(status: AutopilotStatus) -> None:
    """Save autopilot status to disk."""
    AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
    with open(AUTOSAVE_DIR / "status.json", "w") as f:
        json.dump(vars(status), f, indent=2, default=str)


# ── Marketing Content Generator ───────────────────────────────

def generate_marketing_content(
    win_rate: float,
    top_signals: List[Dict],
    weekly_summary: str = "",
) -> str:
    """Generate marketing post content for channel/group.

    Showcases bot capabilities to attract new users.
    """
    now = datetime.now(WIB)

    # Signal highlights
    signal_lines = []
    for s in top_signals[:3]:
        emoji = "🟢" if s.get("is_win") else "🔴"
        signal_lines.append(f"  {emoji} {s['symbol']}: {s.get('pnl_pct', 0):+.1f}%")

    win_emoji = "🔥" if win_rate >= 92 else "📈" if win_rate >= 85 else "📊"

    content = (
        f"🤖 *Vilona Saham — Daily Signal Report*\n"
        f"📅 {now.strftime('%d %B %Y')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{win_emoji} *Win Rate: {win_rate}%* (backtested)\n\n"
        f"*Latest Signals:*\n"
        + "\n".join(signal_lines) +
        f"\n\n"
        f"✅ Swing Trade + Scalping signals\n"
        f"✅ TP/SL otomatis\n"
        f"✅ Daily mapping harian\n"
        f"✅ Backtested setiap minggu\n\n"
        f"💎 Mulai dari Rp79.900/bulan\n"
        f"👉 @VilonaSahamBot /start\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Bukan rekomendasi beli/jual. DYOR."
    )

    return content


def generate_weekly_marketing(
    swing_report,
    scalp_report,
) -> str:
    """Generate weekly marketing showcase content."""
    now = datetime.now(WIB)

    content = (
        f"📊 *Vilona Saham — Weekly Performance*\n"
        f"📅 Minggu {now.strftime('%d %B %Y')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*📈 Swing Trade:*\n"
        f"  Win Rate: {swing_report.win_rate}%\n"
        f"  Total Trades: {swing_report.total_trades}\n"
        f"  Avg Return: {swing_report.avg_return_pct}%\n"
        f"  Best: +{swing_report.best_trade_pct}%\n\n"
        f"*⚡ Scalping:*\n"
        f"  Win Rate: {scalp_report.win_rate}%\n"
        f"  Total Trades: {scalp_report.total_trades}\n"
        f"  Avg Return: {scalp_report.avg_return_pct}%\n"
        f"  Best: +{scalp_report.best_trade_pct}%\n\n"
        f"🔄 Backtested setiap minggu\n"
        f"🎯 Target win rate: 92%+\n"
        f"🤖 Sistem improvement otomatis\n\n"
        f"💎 Mulai dari Rp79.900/bulan\n"
        f"👉 @VilonaSahamBot /start\n"
    )

    return content


# ── Follow-Up Content Templates ───────────────────────────────

FOLLOWUP_TEMPLATES = {
    "new": {
        1: (
            "👋 Halo {name}! Selamat datang di Vilona Saham.\n\n"
            "Kamu sudah coba /analisa BBCA belum? Gratis! 🎉\n\n"
            "Fitur yang tersedia:\n"
            "• Analisa saham + AI insight\n"
            "• Screener otomatis (momentum, reversal, breakout)\n"
            "• Signal harian dengan TP/SL\n\n"
            "Ketik /help untuk lihat semua command."
        ),
        2: (
            "💡 {name}, member Pro kami sudah dapat:\n\n"
            "📈 Signal Swing Trade harian\n"
            "⚡ Signal Scalping harian\n"
            "🎯 TP/SL otomatis\n"
            "📊 Daily mapping pasar\n\n"
            "Coba /signal_swing atau /signal_scalp!\n"
            "Upgrade: /upgrade"
        ),
        3: (
            "🔔 {name}, terakhir nih!\n\n"
            "Kami kasih diskon khusus minggu ini:\n"
            "💎 PRO: Rp79.900/bulan (harga normal Rp149.000)\n\n"
            "Benefit:\n"
            "• Signal harian + TP/SL\n"
            "• Backtested 92%+ win rate\n"
            "• Auto-improvement setiap minggu\n\n"
            "👉 /upgrade sekarang!"
        ),
    },
    "active_free": {
        1: (
            "📊 {name}, kamu sudah {activity}x pakai bot ini!\n\n"
            "Kamu tahu nggak? Member Pro dapat signal harian\n"
            "dengan TP/SL yang di-backtest setiap minggu.\n\n"
            "Coba: /signal_swing atau /signal_scalp\n"
            "Upgrade: /upgrade"
        ),
        2: (
            "⚡ {name}, signal terakhir kami:\n\n"
            "{top_signal}\n\n"
            "Semua signal di-backtest otomatis.\n"
            "Win rate saat ini: {win_rate}%\n\n"
            "Mau akses penuh? /upgrade"
        ),
    },
    "sleeping": {
        1: (
            "👀 {name}, lama nggak ketemu!\n\n"
            "Market lagi seru nih! Beberapa signal hari ini:\n"
            "{hot_stocks}\n\n"
            "Cek sekarang: /signal_swing\n"
        ),
        2: (
            "🔔 {name}, kami kangen! 😄\n\n"
            "Update terbaru:\n"
            "• Signal Swing + Scalping sudah live\n"
            "• Backtesting otomatis setiap minggu\n"
            "• Daily mapping pasar\n\n"
            "Coba gratis: /analisa BBCA"
        ),
    },
    "power_free": {
        1: (
            "🔥 {name}, kamu power user! ({activity} commands)\n\n"
            "Kamu sudah merasakan fitur gratis kami.\n"
            "Bayangkan akses PENUH:\n\n"
            "✅ Signal harian + TP/SL\n"
            "✅ Semua screener unlimited\n"
            "✅ Bandarmologi + Smart Money\n"
            "✅ Backtested win rate 92%+\n\n"
            "💎 PRO: hanya Rp79.900/bulan\n"
            "👉 /upgrade"
        ),
        2: (
            "💎 {name}, penawaran spesial untukmu!\n\n"
            "Karena kamu aktif ({activity} commands),\n"
            "kami kasih harga khusus:\n\n"
            "PRO: Rp69.900/bulan (hemat Rp10.000)\n"
            "Kode: POWER{user_id}\n\n"
            "Berlaku 48 jam! /upgrade"
        ),
    },
    "paid_churn": {
        1: (
            "👋 {name}, subscription kamu sudah expired.\n\n"
            "Kami rindu kamu! Beberapa update terbaru:\n"
            "• Signal Swing + Scalping baru\n"
            "• Backtesting otomatis\n"
            "• Win rate improvement system\n\n"
            "Renew sekarang: /upgrade"
        ),
        2: (
            "🎁 {name}, welcome back offer!\n\n"
            "Renew minggu ini dan dapat:\n"
            "• Diskon 20% bulan pertama\n"
            "• Bonus: akses signal premium 7 hari\n\n"
            "👉 /upgrade"
        ),
    },
}


def get_followup_message(
    segment: str,
    stage: int,
    user_name: str = "Trader",
    user_id: int = 0,
    activity_count: int = 0,
    win_rate: float = 0,
    top_signal: str = "",
    hot_stocks: str = "",
) -> str:
    """Get follow-up message for a specific segment and stage."""
    templates = FOLLOWUP_TEMPLATES.get(segment, {})
    template = templates.get(stage)
    if not template:
        return ""

    return template.format(
        name=user_name,
        user_id=user_id,
        activity=activity_count,
        win_rate=win_rate,
        top_signal=top_signal or "Belum ada signal baru",
        hot_stocks=hot_stocks or "Cek /signal_swing",
    )


# ── Daily Briefing Generator ──────────────────────────────────

async def generate_daily_briefing() -> str:
    """Generate comprehensive daily briefing for channel push.

    Combines: market map + signals + marketing angle.
    """
    from src.engine.market_mapper import generate_daily_map
    from src.engine.signal_engine import scan_signals

    daily_map = await generate_daily_map()
    swing_batch = await scan_signals("swing", limit=3)
    scalp_batch = await scan_signals("scalp", limit=3)

    now = datetime.now(WIB)

    lines = [
        f"☀️ *Good Morning, Trader!*",
        f"📅 {now.strftime('%A, %d %B %Y')}",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
        daily_map.summary,
        "",
    ]

    if swing_batch.signals:
        lines.append("📈 *Signal Swing Hari Ini:*")
        for i, s in enumerate(swing_batch.signals, 1):
            lines.append(
                f"  {i}. *{s.symbol}* | Entry: Rp{s.entry_price:,.0f} | "
                f"TP1: Rp{s.tp1:,.0f} | SL: Rp{s.sl:,.0f} | "
                f"Conf: {s.confidence}"
            )
        lines.append("")

    if scalp_batch.signals:
        lines.append("⚡ *Signal Scalping Hari Ini:*")
        for i, s in enumerate(scalp_batch.signals, 1):
            lines.append(
                f"  {i}. *{s.symbol}* | Entry: Rp{s.entry_price:,.0f} | "
                f"TP1: Rp{s.tp1:,.0f} | SL: Rp{s.sl:,.0f} | "
                f"Conf: {s.confidence}"
            )
        lines.append("")

    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━",
        "💡 Detail: /signal_swing atau /signal_scalp",
        "📊 Analisa: /analisa [kode]",
        "💎 Upgrade: /upgrade",
        "",
        "⚠️ Bukan rekomendasi. DYOR & manajemen risiko!",
    ])

    return "\n".join(lines)


# ── Follow-Up Sweep ───────────────────────────────────────────

async def run_followup_sweep(app) -> Dict[str, int]:
    """Run autonomous follow-up sweep across all user segments.

    Returns counts of messages sent per segment.
    """
    from src.engine.followup import classify_user, Segment
    from src.models import get_engine, User, Subscription, Base
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    status = load_status()
    sent_counts: Dict[str, int] = {"new": 0, "active_free": 0, "sleeping": 0, "power_free": 0, "paid_churn": 0}
    now = datetime.now(WIB)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.is_active == True))
        users = result.scalars().all()

        for user in users:
            segment = classify_user(user)
            if segment is None:
                continue

            # Anti-spam: minimum 48h between follow-ups
            if user.last_followup_at:
                last = user.last_followup_at.replace(tzinfo=WIB) if user.last_followup_at.tzinfo is None else user.last_followup_at
                if (now - last).total_seconds() < 48 * 3600:
                    continue

            # Max 3 follow-ups per user
            stage = user.followup_stage or 0
            if stage >= 3:
                continue

            next_stage = stage + 1
            msg = get_followup_message(
                segment=segment.value if hasattr(segment, 'value') else str(segment),
                stage=next_stage,
                user_name=user.full_name or user.username or "Trader",
                user_id=user.telegram_id or 0,
                activity_count=user.activity_count or 0,
            )

            if not msg or not user.telegram_id:
                continue

            try:
                await app.bot.send_message(chat_id=user.telegram_id, text=msg, parse_mode="Markdown")
                user.followup_stage = next_stage
                user.last_followup_at = now
                seg_key = segment.value if hasattr(segment, 'value') else str(segment)
                sent_counts[seg_key] = sent_counts.get(seg_key, 0) + 1
                status.total_followups_sent += 1
                logger.info(f"Follow-up sent: {user.telegram_id} segment={seg_key} stage={next_stage}")
            except Exception as e:
                logger.warning(f"Follow-up failed for {user.telegram_id}: {e}")

        await session.commit()

    status.last_followup_sweep = now.isoformat()
    save_status(status)

    return sent_counts


# ── Channel Poster ─────────────────────────────────────────────

async def post_daily_to_channel(app, channel_id: Optional[str] = None) -> bool:
    """Post daily briefing to channel."""
    from src.config import settings

    target = channel_id or getattr(settings, 'channel_id', None)
    if not target:
        logger.warning("No channel_id configured for daily post")
        return False

    try:
        briefing = await generate_daily_briefing()
        await app.bot.send_message(chat_id=target, text=briefing, parse_mode="Markdown")

        status = load_status()
        status.last_daily_run = datetime.now(WIB).isoformat()
        status.total_signals_posted += 1
        save_status(status)

        logger.info(f"Daily briefing posted to {target}")
        return True
    except Exception as e:
        logger.error(f"Failed to post daily briefing: {e}")
        return False


async def post_weekly_report(app, channel_id: Optional[str] = None) -> bool:
    """Post weekly backtest report + marketing content to channel."""
    from src.config import settings
    from src.engine.backtester import run_weekly_backtest, format_report_telegram

    target = channel_id or getattr(settings, 'channel_id', None)
    if not target:
        return False

    try:
        # Run backtests
        swing_report = await run_weekly_backtest("swing")
        scalp_report = await run_weekly_backtest("scalp")

        # Format reports
        swing_text = format_report_telegram(swing_report)
        scalp_text = format_report_telegram(scalp_report)

        # Marketing content
        marketing = generate_weekly_marketing(swing_report, scalp_report)

        # Post to channel
        await app.bot.send_message(chat_id=target, text=swing_text, parse_mode="Markdown")
        await app.bot.send_message(chat_id=target, text=scalp_text, parse_mode="Markdown")
        await app.bot.send_message(chat_id=target, text=marketing, parse_mode="Markdown")

        status = load_status()
        status.last_weekly_backtest = datetime.now(WIB).isoformat()
        status.current_win_rate_swing = swing_report.win_rate
        status.current_win_rate_scalp = scalp_report.win_rate
        status.total_marketing_posts += 1
        save_status(status)

        logger.info(f"Weekly report posted to {target}")
        return True
    except Exception as e:
        logger.error(f"Failed to post weekly report: {e}")
        return False
