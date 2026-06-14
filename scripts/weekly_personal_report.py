#!/usr/bin/env python3
"""Weekly Personal Report — sends personalized stats to each active user via Telegram DM.

Run via cron every Monday morning:
    python3 scripts/weekly_personal_report.py [--dry-run]

Dry-run mode prints what would be sent without actually messaging users.
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
from src.engine.value_nudge import (
    compute_personal_stats,
    format_personal_stats,
    SOCIAL_PROOF,
    get_random_testimonial,
)

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))


async def main():
    """Main dispatcher — iterate active users, send personalized weekly stats."""
    from telegram import Bot
    from telegram.error import TelegramError, Forbidden

    dry_run = "--dry-run" in sys.argv

    if not settings.bot_token:
        logger.error("BOT_TOKEN not configured — cannot dispatch")
        return

    bot = Bot(token=settings.bot_token)

    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)

    now = datetime.now(WIB)
    today = now.strftime("%d %B %Y")

    sent_count = 0
    skipped_count = 0
    error_count = 0

    with Session() as session:
        # Get all active users with a telegram_id
        users = (
            session.query(User)
            .filter(User.is_active == True, User.telegram_id.isnot(None))
            .all()
        )

        logger.info(f"Scanning {len(users)} active users for weekly report...")

        for user in users:
            if not user.telegram_id:
                skipped_count += 1
                continue

            # Compute personal stats
            stats = compute_personal_stats(user, session)

            # Skip users with 0 analyses — nothing to report
            if stats["total_analyses"] == 0:
                logger.debug(
                    f"Skipping {user.telegram_id} "
                    f"({user.username or user.full_name}): 0 analyses"
                )
                skipped_count += 1
                continue

            # Format stats card (already includes separator + social proof line)
            stats_card = format_personal_stats(stats)

            # Build final message
            message = (
                f"📊 *Weekly Report — {today}*\n\n"
                f"{stats_card}\n\n"
                f"📖 /panduan | 📊 /mystats"
            )

            if dry_run:
                logger.info(
                    f"[DRY RUN] Would send to {user.telegram_id} "
                    f"({user.username or user.full_name}): "
                    f"{stats['total_analyses']} analyses, "
                    f"tier={stats['tier']}"
                )
                sent_count += 1
                continue

            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode="Markdown",
                )

                logger.info(
                    f"✅ Weekly report sent to {user.telegram_id} "
                    f"({user.username or user.full_name}): "
                    f"{stats['total_analyses']} analyses, "
                    f"tier={stats['tier']}"
                )
                sent_count += 1

                # Rate limit — 1 message per second max (Telegram flood control)
                await asyncio.sleep(1)

            except Forbidden:
                # User blocked the bot — mark inactive
                logger.info(
                    f"🚫 User {user.telegram_id} "
                    f"({user.username or user.full_name}) blocked bot — "
                    f"marking is_active=False"
                )
                user.is_active = False
                session.commit()
                error_count += 1

            except TelegramError as e:
                logger.warning(
                    f"⚠️ Telegram error for {user.telegram_id} "
                    f"({user.username or user.full_name}): {e}"
                )
                error_count += 1

            except Exception as e:
                logger.error(
                    f"❌ Unexpected error for {user.telegram_id} "
                    f"({user.username or user.full_name}): {e}"
                )
                error_count += 1

    engine.dispose()
    try:
        await bot.close()
    except Exception:
        pass  # ignore transient network/rate-limit errors during close

    summary = (
        f"Weekly personal report complete: "
        f"{sent_count} sent, {skipped_count} skipped, {error_count} errors"
    )
    logger.info(summary)
    print(summary)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(main())
