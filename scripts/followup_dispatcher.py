"""
Follow-Up Dispatcher — runs as cron job, sends targeted follow-up DMs.

Flow:
1. Query all free users
2. Classify each user into segment
3. Check if they should receive follow-up (stage, timing, anti-spam)
4. Send follow-up message via Telegram bot
5. Update followup_stage + last_followup_at in DB
"""
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.models import User, Subscription
from src.engine.followup import classify_user, should_followup, get_message, Segment

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))


async def run_followup_dispatcher(dry_run: bool = False):
    """Main dispatcher — iterate users, send follow-ups."""
    from telegram import Bot
    from telegram.error import TelegramError, Forbidden

    if not settings.bot_token:
        logger.error("BOT_TOKEN not configured — cannot dispatch")
        return

    bot = Bot(token=settings.bot_token)

    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)

    now = datetime.now(WIB)
    sent_count = 0
    skipped_count = 0
    error_count = 0

    with Session() as session:
        # Get all free users with their subscriptions
        users = (
            session.query(User)
            .outerjoin(Subscription, User.id == Subscription.user_id)
            .filter(
                (Subscription.tier == "free") | (Subscription.tier == None)
            )
            .all()
        )

        logger.info(f"Scanning {len(users)} free users for follow-up...")

        for user in users:
            # Attach subscription if needed
            if not hasattr(user, 'subscription') or user.subscription is None:
                sub = session.query(Subscription).filter_by(user_id=user.id).first()
                user.subscription = sub

            should_send, segment, next_stage = should_followup(user)
            if not should_send:
                skipped_count += 1
                continue

            message = get_message(Segment(segment), next_stage)
            if not message:
                skipped_count += 1
                continue

            if not user.telegram_id:
                skipped_count += 1
                continue

            if dry_run:
                logger.info(
                    f"[DRY RUN] Would send to {user.telegram_id} "
                    f"({user.username or user.full_name}): segment={segment} stage={next_stage}"
                )
                sent_count += 1
                continue

            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode="Markdown",
                )
                # Update user record
                user.followup_stage = next_stage
                user.last_followup_at = now
                user.followup_segment = segment
                session.commit()

                logger.info(
                    f"✅ Follow-up sent to {user.telegram_id} "
                    f"({user.username or user.full_name}): {segment} stage {next_stage}"
                )
                sent_count += 1

                # Rate limit — 1 msg per second max
                await asyncio.sleep(1)

            except Forbidden:
                # User blocked the bot
                logger.info(f"🚫 User {user.telegram_id} blocked bot — skipping")
                user.is_active = False
                session.commit()
                error_count += 1

            except TelegramError as e:
                logger.warning(f"⚠️ Telegram error for {user.telegram_id}: {e}")
                error_count += 1

            except Exception as e:
                logger.error(f"❌ Unexpected error for {user.telegram_id}: {e}")
                error_count += 1

    engine.dispose()
    await bot.close()

    logger.info(
        f"Follow-up dispatch complete: {sent_count} sent, "
        f"{skipped_count} skipped, {error_count} errors"
    )

    return {
        "sent": sent_count,
        "skipped": skipped_count,
        "errors": error_count,
        "total_users": len(users),
    }


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_followup_dispatcher(dry_run=dry_run))
