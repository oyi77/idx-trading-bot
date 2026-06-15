"""
Onboarding Drip — 3-stage welcome DM sequence for new users.

Timing (based on hours since created_at):
  Stage 1 (H+1  to H+2 ): Welcome message + quick start
  Stage 2 (H+3  to H+4 ): Feature showcase
  Stage 3 (H+7  to H+8 ): Upgrade offer

Guard:
- Only users created within the last 7 days
- activity_count < 10 (they're still learning the product)
- Don't send if onboarding_stage already marks this stage done
- If user exceeds 10 activity_count at scan time, skip entirely
- Handle Forbidden (blocked bot)
- Rate limit: 1 second between messages

Run:
  python scripts/onboarding_drip.py             # live
  python scripts/onboarding_drip.py --dry-run   # preview only
"""
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.models import User, Subscription

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

# ── Message templates ──

STAGE_MESSAGES = {
    1: (
        "👋 *Welcome to Vilona Saham!*\n\n"
        "Lo udah join — sekarang saatnya cuan. Quick start:\n\n"
        "1️⃣ `/analisa BBCA` — AI full breakdown\n"
        "2️⃣ `/screener momentum` — saham trending\n"
        "3️⃣ `/alert TLKM >4000` — notifikasi harga\n\n"
        "📖 Panduan lengkap: /panduan\n"
        "🔥 Coba sekarang, gratis kok!"
    ),
    2: (
        "📊 *Day 3 — Udah nyobain fitur keren?*\n\n"
        "Yang trader pro pake:\n"
        "• `/screener breakout` — saham breakout\n"
        "• `/bandarmology` — jejak bandar asing\n"
        "• `/plan BBCA` — trading plan otomatis\n\n"
        "💎 Lo masih free. Upgrade ke Pro: /upgrade"
    ),
    3: (
        "🚀 *7 hari bareng Vilona Saham!*\n\n"
        "Lo udah explore fitur gratis. Sekarang saatnya:\n"
        "• Real-time data (no delay)\n"
        "• 50 alert + bandarmology\n"
        "• Screener unlimited\n\n"
        "💎 Pro cuma Rp49rb/bln — /upgrade\n"
        "💰 Cancel kapan aja."
    ),
}

# ── Stage timing windows (hours since created_at) ──

STAGE_WINDOWS = {
    1: (1, 2),   # H+1 to H+2
    2: (3, 4),   # H+3 to H+4
    3: (7, 8),   # H+7 to H+8
}

MAX_ACTIVITY_COUNT = 10
MAX_ACCOUNT_AGE_DAYS = 7


REQUIRED_COLUMNS = {
    "onboarding_stage": "INTEGER DEFAULT 0",
    "last_watchlist_alert_at": "DATETIME",
}


def ensure_columns(engine) -> None:
    """Add any missing columns to the users table."""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(users)"))
        existing = {row[1] for row in result.fetchall()}
        for col_name, col_def in REQUIRED_COLUMNS.items():
            if col_name not in existing:
                logger.info(f"Adding {col_name} column to users table...")
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                conn.commit()
                logger.info(f"✅ {col_name} column added")
            else:
                logger.debug(f"{col_name} column already exists")


def stage_in_window(hours_since_created: float, stage: int) -> bool:
    """Check if hours_since_created falls inside the stage's send window."""
    lo, hi = STAGE_WINDOWS[stage]
    return lo <= hours_since_created <= hi


async def run_onboarding_drip(dry_run: bool = False):
    """Main onboarding dispatcher — iterate new users, send stage messages."""
    from telegram import Bot
    from telegram.error import TelegramError, Forbidden

    if not settings.bot_token:
        logger.error("BOT_TOKEN not configured — cannot dispatch")
        return

    bot = Bot(token=settings.bot_token)

    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)

    # Ensure required columns exist in DB
    ensure_columns(engine)

    Session = sessionmaker(bind=engine)

    now = datetime.now(WIB)
    cutoff_date = now - timedelta(days=MAX_ACCOUNT_AGE_DAYS)

    sent_count = 0
    skipped_count = 0
    error_count = 0

    with Session() as session:
        # Query: users created in last 7 days, activity_count < 10
        users = (
            session.query(User)
            .outerjoin(Subscription, User.id == Subscription.user_id)
            .filter(
                User.created_at >= cutoff_date,
                User.activity_count < MAX_ACTIVITY_COUNT,
                User.is_active == True,
            )
            .all()
        )

        logger.info(f"Scanning {len(users)} recent users for onboarding drip...")

        for user in users:
            if not user.telegram_id:
                skipped_count += 1
                continue

            # Check if user has exceeded activity threshold (re-check at scan time)
            if user.activity_count and user.activity_count >= MAX_ACTIVITY_COUNT:
                skipped_count += 1
                continue

            # Calculate hours since signup
            now_utc = datetime.now(WIB)
            created = user.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=WIB)
            hours_since = (now_utc - created).total_seconds() / 3600

            # Determine which stage (if any) the user is in
            onboarding_stage = getattr(user, "onboarding_stage", 0) or 0
            target_stage = None

            for stage in (1, 2, 3):
                if onboarding_stage >= stage:
                    # Already delivered this stage
                    continue
                if stage_in_window(hours_since, stage):
                    target_stage = stage
                    break

            if target_stage is None:
                skipped_count += 1
                continue

            message = STAGE_MESSAGES.get(target_stage)
            if not message:
                skipped_count += 1
                continue

            if dry_run:
                logger.info(
                    f"[DRY RUN] Would send stage {target_stage} to "
                    f"tg://{user.telegram_id} ({user.username or user.full_name}) "
                    f"— joined {hours_since:.1f}h ago, activity={user.activity_count}"
                )
                sent_count += 1
                continue

            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode="Markdown",
                )

                # Update onboarding_stage
                user.onboarding_stage = target_stage
                session.commit()

                logger.info(
                    f"✅ Stage {target_stage} sent to tg://{user.telegram_id} "
                    f"({user.username or user.full_name})"
                )
                sent_count += 1

                # Rate limit: 1 msg/sec
                await asyncio.sleep(1)

            except Forbidden:
                logger.info(f"🚫 User {user.telegram_id} blocked bot — marking inactive")
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
    try:
        await asyncio.sleep(0.3)
        await bot.close()
    except Exception:
        pass  # bot.close() can hit rate limits — non-critical

    logger.info(
        f"Onboarding drip complete: {sent_count} sent, "
        f"{skipped_count} skipped, {error_count} errors"
    )

    return {
        "sent": sent_count,
        "skipped": skipped_count,
        "errors": error_count,
        "total_users": len(users) if "users" in dir() else 0,
    }


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        logger.info("🔍 DRY RUN MODE — no messages will be sent")
    result = await run_onboarding_drip(dry_run=dry_run)
    logger.info(f"Summary: {result}")


if __name__ == "__main__":
    asyncio.run(main())
