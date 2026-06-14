#!/usr/bin/env python3
"""
Notification Dispatcher — Vilona Saham
======================================
Jalan tiap 15 menit via cron. Cek alert, trading plan, trial expiry,
lalu kirim notifikasi langsung ke Telegram user.

Notif types:
  1. Alert harga tercapai
  2. Trading plan kena SL/TP
  3. Watchlist digest (hanya jam 07:00)
  4. Trial expiry reminder
  5. Weekly report (hanya Senin 08:00)
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import yfinance as yf
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

# ── Setup ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("notif-dispatcher")

# Paths
# Script lives in ~/.hermes/scripts/ but project is in ~/idx-trading-bot/
PROJECT_DIR = Path.home() / "idx-trading-bot"
sys.path.insert(0, str(PROJECT_DIR))
os.chdir(str(PROJECT_DIR))

from src.config import settings
from src.models import Base, User, Subscription, TradePlan, Alert, AnalysisJournal

BOT_TOKEN = settings.bot_token
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Price cache — hindari repeated API calls dalam satu run
_price_cache: dict[str, float | None] = {}

# ── Telegram Sender ────────────────────────────────────────

async def send_telegram(chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
    """Kirim pesan ke user via Telegram Bot API."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
            )
            data = resp.json()
            if data.get("ok"):
                return True
            logger.warning(f"Telegram send failed: {data.get('description', 'unknown')}")
            return False
    except Exception as e:
        logger.error(f"Telegram API error: {e}")
        return False


# ── Price Fetcher ──────────────────────────────────────────

def fetch_price(symbol: str) -> float | None:
    """Fetch latest price with caching."""
    if symbol in _price_cache:
        return _price_cache[symbol]

    try:
        ticker = yf.Ticker(f"{symbol}.JK")
        # Gunakan fast_info untuk data terbaru tanpa history overhead
        price = ticker.fast_info.last_price
        if price and price > 0:
            _price_cache[symbol] = float(price)
            return _price_cache[symbol]

        # Fallback: coba history 1 hari
        hist = ticker.history(period="1d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            _price_cache[symbol] = price
            return price
    except Exception as e:
        logger.warning(f"Price fetch failed for {symbol}: {e}")

    _price_cache[symbol] = None
    return None


def fetch_prices_bulk(symbols: list[str]) -> dict[str, float | None]:
    """Fetch multiple prices efficiently."""
    results: dict[str, float | None] = {}
    uncached = [s for s in symbols if s not in _price_cache]

    if uncached:
        try:
            tickers = yf.Tickers(" ".join(f"{s}.JK" for s in uncached))
            for s in uncached:
                try:
                    t = tickers.tickers.get(f"{s}.JK")
                    if t:
                        price = t.fast_info.last_price
                        if price and price > 0:
                            results[s] = float(price)
                            _price_cache[s] = float(price)
                            continue
                except Exception:
                    pass
                results[s] = None
                _price_cache[s] = None
        except Exception as e:
            logger.warning(f"Bulk fetch failed: {e}")
            # Fallback individual
            for s in uncached:
                results[s] = fetch_price(s)

    # Merge cached
    for s in symbols:
        if s not in results:
            results[s] = _price_cache.get(s)

    return results


# ── DB Session Helper ──────────────────────────────────────

def get_session():
    """Create sync DB session."""
    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session(), engine


# ═══════════════════════════════════════════════════════════
#  NOTIFICATION DISPATCHERS
# ═══════════════════════════════════════════════════════════

def check_alerts(session) -> list[dict]:
    """Cek semua alert aktif & belum triggered. Return list notif yang harus dikirim."""
    active_alerts = (
        session.query(Alert)
        .filter(Alert.is_active == True, Alert.is_triggered == False)
        .all()
    )

    if not active_alerts:
        return []

    # Kumpulkan simbol unik
    symbols = list(set(a.symbol for a in active_alerts))
    prices = fetch_prices_bulk(symbols)

    notifications = []
    for alert in active_alerts:
        price = prices.get(alert.symbol)
        if price is None:
            continue

        triggered = False
        if alert.condition == ">":
            triggered = price > alert.value
        elif alert.condition == "<":
            triggered = price < alert.value
        elif alert.condition == ">=":
            triggered = price >= alert.value
        elif alert.condition == "<=":
            triggered = price <= alert.value

        if not triggered:
            continue

        # Mark as triggered
        alert.is_triggered = True
        alert.triggered_at = datetime.utcnow()

        # Get user
        user = session.query(User).filter(User.id == alert.user_id).first()
        if not user or not user.telegram_id:
            continue

        direction = "naik" if price > alert.value else "turun"
        emoji = "🟢" if price > alert.value else "🔴"
        text = (
            f"{emoji} *Alert Tercapai!* — {alert.symbol}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Harga sekarang: *Rp{price:,.0f}*\n"
            f"Kondisi: {alert.symbol} {alert.condition} Rp{alert.value:,.0f}\n"
            f"Harga {direction} *Rp{abs(price - alert.value):,.0f}*\n\n"
            f"📊 Analisa: `analisa {alert.symbol}`"
        )

        notifications.append({
            "chat_id": user.telegram_id,
            "text": text,
            "type": "alert",
        })

    session.commit()
    return notifications


def check_trading_plans(session) -> list[dict]:
    """Cek plan aktif yg kena SL/TP. Auto-close & kirim notif."""
    active_plans = (
        session.query(TradePlan)
        .join(User)
        .filter(
            TradePlan.status == "active",
            TradePlan.auto_report == True,
        )
        .all()
    )

    if not active_plans:
        return []

    symbols = list(set(p.symbol for p in active_plans))
    prices = fetch_prices_bulk(symbols)

    notifications = []
    for plan in active_plans:
        user = session.query(User).filter(User.id == plan.user_id).first()
        if not user or not user.telegram_id:
            continue

        price = prices.get(plan.symbol)
        if price is None:
            continue

        hit_tp = False
        hit_sl = False

        if plan.take_profit and plan.direction == "long":
            hit_tp = price >= plan.take_profit
        elif plan.take_profit and plan.direction == "short":
            hit_tp = price <= plan.take_profit

        if plan.stop_loss and plan.direction == "long":
            hit_sl = price <= plan.stop_loss
        elif plan.stop_loss and plan.direction == "short":
            hit_sl = price >= plan.stop_loss

        if not hit_tp and not hit_sl:
            continue

        # Hitung P&L
        if hit_tp:
            plan.status = "hit_tp"
            pnl = abs(plan.take_profit - plan.entry_price)
            emoji = "✅"
            label = "TP Tercapai!"
            detail = f"Profit: *+Rp{pnl:,.0f}* (R:R {plan.risk_reward}x)"
        else:
            plan.status = "hit_sl"
            pnl = abs(plan.entry_price - plan.stop_loss)
            emoji = "❌"
            label = "SL Kena!"
            detail = f"Loss: *-Rp{pnl:,.0f}*"

        plan.updated_at = datetime.utcnow()

        text = (
            f"{emoji} *{label}* — {plan.symbol}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Entry: Rp{plan.entry_price:,.0f}\n"
            f"SL: Rp{plan.stop_loss:,.0f} | TP: Rp{plan.take_profit:,.0f}\n"
            f"Harga sekarang: *Rp{price:,.0f}*\n"
            f"{detail}\n\n"
            f"📊 Cek performa: /performance"
        )

        notifications.append({
            "chat_id": user.telegram_id,
            "text": text,
            "type": "trade_plan",
        })

    session.commit()
    return notifications


def check_trial_expiry(session) -> list[dict]:
    """Cek user trial yg mau habis. Kirim reminder 3 hari, 1 hari, expired."""
    now = datetime.utcnow()

    # Cari subscription trial aktif
    trials = (
        session.query(Subscription)
        .join(User)
        .filter(
            Subscription.tier.in_(["pro", "premium"]),
            Subscription.payment_status == "trial",
            Subscription.end_date.isnot(None),
        )
        .all()
    )

    notifications = []
    for sub in trials:
        user = session.query(User).filter(User.id == sub.user_id).first()
        if not user or not user.telegram_id:
            continue

        remaining = sub.end_date - now
        days_left = remaining.days

        # Kirim notif kalau tersisa 3, 1, atau 0 hari
        if days_left in (3, 1, 0):
            tier_label = "Pro" if sub.tier == "pro" else "Premium"
            price_label = "Rp49rb" if sub.tier == "pro" else "Rp149rb"

            if days_left > 0:
                text = (
                    f"⏰ *Trial {tier_label} Hampir Habis*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Tersisa *{days_left} hari* lagi.\n\n"
                    f"Jangan kehilangan akses ke:\n"
                    f"• Screener 4 kategori\n"
                    f"• Trading plan + 50 alert\n"
                    f"• Real-time data\n\n"
                    f"💰 Upgrade sekarang cuma *{price_label}/bulan*\n"
                    f"👉 /upgrade {sub.tier}"
                )
            else:
                text = (
                    f"😢 *Trial {tier_label} Habis*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Fitur {tier_label} udah nggak aktif.\n\n"
                    f"Tapi lo masih bisa pake Free tier.\n"
                    f"Kangen fitur lengkap?\n\n"
                    f"💰 *{price_label}/bulan* — /upgrade {sub.tier}"
                )
                # Downgrade ke free
                sub.tier = "free"
                sub.payment_status = "expired"

            notifications.append({
                "chat_id": user.telegram_id,
                "text": text,
                "type": "trial_expiry",
            })

    session.commit()
    return notifications


async def check_watchlist_digest(session) -> list[dict]:
    """Watchlist digest — hanya jam 07:00-08:00 WIB (00:00-01:00 UTC)."""
    now = datetime.utcnow()
    if now.hour != 0:
        return []

    from src.engine.watchlist import WatchlistEngine

    engine = WatchlistEngine()

    pros = (
        session.query(Subscription)
        .filter(Subscription.tier.in_(["pro", "premium", "lifetime"]))
        .all()
    )

    notifications = []
    for sub in pros:
        user = session.query(User).filter(User.id == sub.user_id).first()
        if not user or not user.telegram_id:
            continue

        try:
            digest = await engine.generate_digest(user.telegram_id)
            if not digest or not digest.entries:
                continue

            text = engine.format_digest(digest)

            notifications.append({
                "chat_id": user.telegram_id,
                "text": text,
                "type": "watchlist_digest",
            })
        except Exception as e:
            logger.warning(f"Watchlist digest failed for {user.telegram_id}: {e}")

    return notifications


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

async def main():
    logger.info("=" * 50)
    logger.info("Notif Dispatcher — starting")

    session, engine = get_session()

    try:
        all_notifs: list[dict] = []

        # 1. Alert check
        logger.info("Checking alerts...")
        alerts = check_alerts(session)
        all_notifs.extend(alerts)
        logger.info(f"  → {len(alerts)} triggered")

        # 2. Trading plan SL/TP check
        logger.info("Checking trading plans...")
        plans = check_trading_plans(session)
        all_notifs.extend(plans)
        logger.info(f"  → {len(plans)} hit SL/TP")

        # 3. Trial expiry
        logger.info("Checking trial expiry...")
        trials = check_trial_expiry(session)
        all_notifs.extend(trials)
        logger.info(f"  → {len(trials)} expiring")

        # 4. Watchlist digest (pagi doang)
        logger.info("Checking watchlist digest...")
        digests = await check_watchlist_digest(session)
        all_notifs.extend(digests)
        logger.info(f"  → {len(digests)} digests")

        # ── Send all notifications ──────────────────────────
        sent = 0
        failed = 0
        for notif in all_notifs:
            success = await send_telegram(notif["chat_id"], notif["text"])
            if success:
                sent += 1
                logger.info(f"  ✅ {notif['type']} → chat {notif['chat_id']}")
            else:
                failed += 1
                logger.warning(f"  ❌ {notif['type']} → chat {notif['chat_id']}")

        logger.info(f"Sent: {sent} | Failed: {failed}")
        logger.info("Notif Dispatcher — done")

    except Exception as e:
        logger.error(f"Dispatcher error: {e}", exc_info=True)
    finally:
        engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
