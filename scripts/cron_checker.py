"""Cron job — check all active alerts and trading plans.
Silent mode: only outputs when alerts/plans actually trigger."""
import asyncio, sys, os

# Ensure src is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import get_engine, Base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# Suppress SQLAlchemy echo — engine uses settings.debug
from src.config import settings
settings.debug = False


async def check_all():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db = Session()

    results = []

    try:
        # 1. Check alerts
        from src.engine.alerter import AlertEngine
        alerter = AlertEngine(db)
        triggered = await alerter.check_all_alerts()

        for alert, user, msg in triggered:
            results.append((user.telegram_id, msg))

        # 2. Check trading plans
        from src.engine.plan import TradePlanEngine
        planner = TradePlanEngine(db)
        plan_updates = await planner.evaluate_plans()

        for plan, user, msg in plan_updates:
            results.append((user.telegram_id, msg))

    finally:
        await db.close()

    # Send notifications via Telegram Bot API
    if results:
        import requests
        for chat_id, msg in results:
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": msg,
                        "parse_mode": "Markdown",
                    },
                    timeout=10,
                )
            except Exception:
                pass  # silently fail — no spam

    # Silent when nothing triggered — no output = no delivery to Telegram

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_all())
