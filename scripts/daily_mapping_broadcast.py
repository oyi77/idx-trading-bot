#!/usr/bin/env python3
"""IDX Daily Market Mapping — broadcast to users based on tier.

- Pro/Premium/Lifetime: full mapping via DM
- Free: marketing notification "upgrade to see mapping"
"""
import asyncio
import sys
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WIB = timezone(timedelta(hours=7))


async def main():
    from src.config import settings
    from src.models import User, Subscription, SubscriptionTier
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    # ── Generate mapping ──
    print(f"[{datetime.now(WIB).strftime('%H:%M')} WIB] Generating daily mapping...")
    try:
        from src.engine.market_mapper import generate_daily_map
        daily = await generate_daily_map()
        mapping = daily.summary
        print(f"  ✓ Mapping generated: {len(mapping)} chars")
    except Exception as e:
        print(f"  ✗ Mapping generation failed: {e}")
        return

    if not mapping or mapping == "Data tidak tersedia — market mungkin belum buka.":
        print("  ⚠ No data available, skipping broadcast")
        return

    # ── Connect DB ──
    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # ── Get all paid users ──
        paid_tiers = (SubscriptionTier.PRO, SubscriptionTier.PREMIUM, SubscriptionTier.LIFETIME, SubscriptionTier.WHITELABEL)
        paid_subs = session.query(Subscription).filter(Subscription.tier.in_(paid_tiers)).all()
        paid_user_ids = {s.user_id for s in paid_subs}

        paid_users = session.query(User).filter(User.id.in_(paid_user_ids), User.telegram_id.isnot(None)).all()
        free_users = session.query(User).filter(
            ~User.id.in_(paid_user_ids),
            User.telegram_id.isnot(None),
        ).all()

        # ── Build full mapping message ──
        now = datetime.now(WIB)
        mapping_msg = (
            f"📊 *DAILY MARKET MAPPING — IDX*\n"
            f"📅 {now.strftime('%A, %d %B %Y')} | {now.strftime('%H:%M')} WIB\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{mapping}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 *Vilona Saham IDX* — AI Trading Co-Pilot\n"
            f"💎 /upgrade untuk akses penuh"
        )

        # Marketing for free users
        free_msg = (
            f"📊 *Daily Market Mapping*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Signal mapping harian sudah terkirim ke member *Pro*, *Premium* & *Lifetime* 🚀\n\n"
            f"📈 Dapatkan signal harian dengan:\n"
            f"✅ Entry Zone + TP/SL otomatis\n"
            f"✅ 11 AI engine analisa paralel\n"
            f"✅ Backtested win rate\n\n"
            f"💎 Upgrade sekarang: /upgrade\n"
            f"🔥 Mulai dari Rp79.900/bulan"
        )

    finally:
        session.close()
    engine.dispose()

    # ── Send via Telegram bot ──
    from src.bot.telegram import create_app
    app = create_app()
    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(1)

    sent = {"paid": 0, "free_marketing": 0, "failed": 0}

    print(f"  Sending to {len(paid_users)} paid users...")
    for user in paid_users:
        try:
            await app.bot.send_message(chat_id=user.telegram_id, text=mapping_msg, parse_mode="Markdown")
            sent["paid"] += 1
            print(f"    ✓ {user.telegram_id} ({user.full_name or user.username})")
        except Exception as e:
            sent["failed"] += 1
            print(f"    ✗ {user.telegram_id}: {e}")
        await asyncio.sleep(0.3)  # Rate limit

    print(f"  Sending marketing to {len(free_users)} free users...")
    for user in free_users:
        try:
            await app.bot.send_message(chat_id=user.telegram_id, text=free_msg, parse_mode="Markdown")
            sent["free_marketing"] += 1
            print(f"    ✓ {user.telegram_id} ({user.full_name or user.username})")
        except Exception as e:
            sent["failed"] += 1
            print(f"    ✗ {user.telegram_id}: {e}")
        await asyncio.sleep(0.3)  # Rate limit

    print(f"\n{'='*40}")
    print(f"  ✅ Done: {sent['paid']} paid + {sent['free_marketing']} marketing")
    print(f"  ❌ Failed: {sent['failed']}")
    print(f"{'='*40}")

    await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
