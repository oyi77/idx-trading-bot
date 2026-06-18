"""Scalev webhook endpoint for jasahub.id/p/vilona-saham payment callbacks."""
import json
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/notify")
async def scalev_notify(request: Request):
    """Receive Scalev payment notification and auto-upgrade user."""
    try:
        body = await request.body()
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    signature = request.headers.get("X-Scalev-Signature") or request.headers.get("X-Webhook-Signature")
    if signature:
        from src.services.scalev import verify_webhook

        if not verify_webhook(body, signature):
            logger.warning("Invalid Scalev signature")
            raise HTTPException(status_code=403, detail="Invalid signature")

    from src.services.scalev import parse_event, extract_reference, mark_paid

    event = parse_event(payload)
    event_name = event["event"]
    reference = extract_reference(event)

    if event_name not in ("payment.paid", "payment.success", "order.paid", "checkout.completed", "paid"):
        return {"status": "ignored", "event": event_name}

    if not reference:
        logger.warning("Scalev callback missing reference")
        return {"status": "ignored", "reason": "missing_reference"}

    mark_paid(reference)
    logger.info(f"Scalev payment marked paid: ref={reference}")

    # ── Auto-upgrade user tier + send Telegram notification ──────
    try:
        from src.services.scalev import _load_payments, infer_tier_from_amount, normalize_amount
        payments_data = _load_payments()
        entry = payments_data.get("payments", {}).get(reference, {})
        user_id = entry.get("user_id")
        tier = entry.get("tier") or infer_tier_from_amount(normalize_amount(entry.get("amount", 0)))
        amount = entry.get("amount", 0)

        if user_id and tier:
            import asyncio
            from src.config import settings
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.ext.asyncio import AsyncSession

            sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
            engine = create_engine(sync_url)
            SessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async def _do_upgrade():
                try:
                    async with SessionFactory() as s:
                        from src.services.user_manager import UserManager
                        mgr = UserManager(s)
                        ok, msg = await mgr.upgrade_tier(user_id, tier, amount)
                        logger.info(f"Auto-upgrade user={user_id} tier={tier}: {ok} {msg}")
                except Exception as e:
                    logger.error(f"Auto-upgrade DB failed: {e}")

            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_do_upgrade())
            else:
                loop.run_until_complete(_do_upgrade())
            engine.dispose()

            # Send Telegram notification
            try:
                from telegram import Bot
                bot = Bot(token=settings.bot_token)
                tier_emoji = {"pro": "💎", "premium": "👑", "lifetime": "🌟"}.get(tier, "✅")
                msg_text = (
                    f"{tier_emoji} *Upgrade Berhasil!*\n\n"
                    f"Akun kamu sekarang *{tier.upper()}*.\n"
                    f"Semua fitur {tier.title()} udah aktif.\n\n"
                    f"Ketik /start untuk mulai pakai!"
                )
                if loop.is_running():
                    loop.create_task(bot.send_message(chat_id=user_id, text=msg_text, parse_mode="Markdown"))
                else:
                    loop.run_until_complete(bot.send_message(chat_id=user_id, text=msg_text, parse_mode="Markdown"))
            except Exception as e:
                logger.warning(f"Telegram upgrade notification failed: {e}")
        else:
            logger.warning(f"Cannot auto-upgrade: user_id={user_id} tier={tier}")
    except Exception as e:
        logger.error(f"Auto-upgrade flow failed: {e}")

    return {"status": "ok", "reference": reference}


@router.post("/payments/notify")
async def scalev_notify_alias(request: Request):
    return await scalev_notify(request)
