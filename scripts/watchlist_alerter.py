#!/usr/bin/env python3
"""
Watchlist Alerter — monitors users' favorite stocks and DMs on >3% moves.

Run via cron. For each user:
1. Query all active users from DB
2. For each user, get their top 3 analyzed stocks from AnalysisJournal
3. Get current quote via RapidAPIFeed (async)
4. If any stock moved >3%, build alert message
5. DM via Telegram Bot (rate-limited 1 sec, anti-spam 24h cooldown)
6. Dry-run mode, summary output

Usage:
    python scripts/watchlist_alerter.py           # live mode
    python scripts/watchlist_alerter.py --dry     # dry-run
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.models import User, AnalysisJournal
from src.feed.rapidapi_idx import RapidAPIFeed

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

DRY_RUN = "--dry" in sys.argv or "--dry-run" in sys.argv

# ── Configuration ─────────────────────────────────────────────────

THRESHOLD_PCT = 3.0          # minimum % move to trigger alert
TOP_N_STOCKS = 3             # how many favorite stocks to monitor per user
RATE_LIMIT_SEC = 1.0         # seconds between Telegram messages
COOLDOWN_HOURS = 24          # don't re-alert same user within this window


# ── Alert Builder (inlined from value_nudge.py build_watchlist_alert) ──

def build_alert_message(user_name: str, movers: list) -> str | None:
    """Build watchlist alert message for a user.

    Inlined from value_nudge.build_watchlist_alert() because the original
    takes a 'feed' parameter that would require additional wiring for
    async RapidAPIFeed calls made externally.

    Args:
        user_name: display name of the user (username or full_name)
        movers: list of (symbol, change_pct, price) tuples

    Returns:
        Formatted Markdown message string, or None if no movers.
    """
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


# ── Quote Fetcher ─────────────────────────────────────────────────

async def get_stock_change(feed: RapidAPIFeed, symbol: str) -> dict | None:
    """Get current price and daily change % for a stock.

    Uses RapidAPI klines endpoint to fetch last 2 daily candles,
    computing change from previous close to current close.

    Args:
        feed: RapidAPIFeed instance (session managed externally)
        symbol: stock symbol (e.g. 'BBCA', 'TLKM')

    Returns:
        dict with keys: price, change_pct, prev_close — or None on failure.
    """
    try:
        candles = await feed.get_klines(symbol, interval="daily", limit=2)
        if not candles or len(candles) < 2:
            # Fall back to single latest candle — no change data possible
            candle = await feed.get_latest_price(symbol)
            if candle:
                close = float(candle.get("close", 0) or 0)
                return {"price": close, "change_pct": 0.0, "prev_close": close}
            return None

        prev_close = float(candles[-2].get("close", 0) or 0)
        curr_close = float(candles[-1].get("close", 0) or 0)

        if prev_close == 0:
            return None

        change_pct = ((curr_close - prev_close) / prev_close) * 100

        return {
            "price": curr_close,
            "change_pct": round(change_pct, 2),
            "prev_close": prev_close,
        }
    except Exception as e:
        logger.warning(f"Failed to get price for {symbol}: {e}")
        return None


# ── Main ──────────────────────────────────────────────────────────

async def main():
    """Main entry point — run via `asyncio.run(main())`."""

    # ── Database setup (sync engine, same pattern as followup_dispatcher) ──
    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)

    # ── Telegram bot ──
    from telegram import Bot
    from telegram.error import TelegramError, Forbidden

    if not settings.bot_token:
        print("[WatchlistAlerter] BOT_TOKEN not configured — aborting")
        return

    bot = Bot(token=settings.bot_token)

    # ── RapidAPI feed ──
    feed = RapidAPIFeed()

    now = datetime.now(WIB)
    cooldown_cutoff = now - timedelta(hours=COOLDOWN_HOURS)

    # ── Counters ──
    users_alerted = 0
    stocks_moved = 0
    errors = 0
    skipped_no_data = 0
    skipped_recent = 0

    with Session() as session:
        # Query all active users with a Telegram ID
        users = (
            session.query(User)
            .filter(
                User.telegram_id.isnot(None),
                User.is_active == True,
            )
            .all()
        )

        mode_label = "DRY RUN" if DRY_RUN else "LIVE"
        print(
            f"[WatchlistAlerter] {now.strftime('%H:%M WIB')} — "
            f"{mode_label} — Scanning {len(users)} users"
        )

        for user in users:
            # ── 24h cooldown guard ──
            last_alert = getattr(user, "last_watchlist_alert_at", None)
            if last_alert is not None and last_alert > cooldown_cutoff:
                skipped_recent += 1
                continue

            # ── Top N analyzed stocks ──
            top = (
                session.query(
                    AnalysisJournal.symbol,
                    func.count(AnalysisJournal.id),
                )
                .filter(AnalysisJournal.user_id == user.id)
                .group_by(AnalysisJournal.symbol)
                .order_by(func.count(AnalysisJournal.id).desc())
                .limit(TOP_N_STOCKS)
                .all()
            )

            if not top:
                skipped_no_data += 1
                continue

            # ── Fetch quotes concurrently ──
            tasks = [get_stock_change(feed, symbol) for symbol, _ in top]
            quotes = await asyncio.gather(*tasks, return_exceptions=True)

            # ── Check for >3% movers ──
            movers = []
            for (symbol, _), quote in zip(top, quotes):
                if isinstance(quote, Exception):
                    logger.warning(f"Quote error for {symbol}: {quote}")
                    continue
                if quote and abs(quote.get("change_pct", 0.0)) >= THRESHOLD_PCT:
                    movers.append((symbol, quote["change_pct"], quote["price"]))

            if not movers:
                continue

            stocks_moved += len(movers)

            # ── Build alert message ──
            display_name = user.username or user.full_name or f"User{user.telegram_id}"
            message = build_alert_message(display_name, movers)
            if not message:
                continue

            # ── Dry-run mode ──
            if DRY_RUN:
                symbols_str = ", ".join(s for s, _, _ in movers)
                print(
                    f"  [DRY] {user.telegram_id} ({display_name}): "
                    f"{symbols_str}"
                )
                users_alerted += 1
                continue

            # ── Send via Telegram ──
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode="Markdown",
                )

                # Update cooldown timestamp
                user.last_watchlist_alert_at = now
                session.commit()

                symbols_str = ", ".join(s for s, _, _ in movers)
                print(
                    f"  ✅ {user.telegram_id} ({display_name}): "
                    f"{symbols_str}"
                )
                users_alerted += 1

                # Rate limit between messages
                await asyncio.sleep(RATE_LIMIT_SEC)

            except Forbidden:
                # User blocked the bot
                print(f"  🚫 {user.telegram_id} blocked bot — deactivating")
                user.is_active = False
                session.commit()
                errors += 1

            except TelegramError as e:
                print(f"  ⚠️ {user.telegram_id} Telegram error: {e}")
                errors += 1

            except Exception as e:
                logger.error(f"  ❌ {user.telegram_id} unexpected: {e}")
                errors += 1

    # ── Cleanup ──
    await feed.close()
    try:
        await asyncio.sleep(0.5)
        await bot.close()
    except Exception:
        pass  # Telegram may rate-limit close()
    engine.dispose()

    # ── Summary ──
    print()
    print(
        f"[WatchlistAlerter] Done: {users_alerted} users alerted, "
        f"{stocks_moved} stocks moved, {errors} errors, "
        f"{skipped_recent} skipped (recent), {skipped_no_data} skipped (no data)"
    )
    print(f"  Mode: {mode_label}")

    return {
        "users_alerted": users_alerted,
        "stocks_moved": stocks_moved,
        "errors": errors,
        "skipped_recent": skipped_recent,
        "skipped_no_data": skipped_no_data,
        "dry_run": DRY_RUN,
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    asyncio.run(main())
