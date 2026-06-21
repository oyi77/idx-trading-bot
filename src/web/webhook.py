"""Scalev webhook endpoint for jasahub.id/p/vilona-saham payment callbacks."""
import json
import logging
import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/midtrans")
async def midtrans_notify(request: Request):
    """Receive Midtrans payment notification and auto-upgrade user."""
    try:
        body = await request.body()
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Verify signature
    order_id = payload.get("order_id", "")
    status_code = payload.get("status_code", "")
    gross_amount = payload.get("gross_amount", "")
    signature_key = payload.get("signature_key", "")

    from src.services.midtrans import verify_signature

    if not verify_signature(order_id, status_code, gross_amount, signature_key):
        logger.warning(f"Invalid Midtrans signature: order_id={order_id}")
        raise HTTPException(status_code=403, detail="Invalid signature")

    transaction_status = payload.get("transaction_status", "")
    
    # Only process successful payments
    if transaction_status not in ("capture", "settlement"):
        return {"status": "ignored", "transaction_status": transaction_status}

    from src.services.midtrans import mark_paid, get_payment, infer_tier_from_amount

    mark_paid(order_id)
    logger.info(f"Midtrans payment marked paid: order_id={order_id}")

    # Auto-upgrade user tier
    try:
        payment_record = get_payment(order_id)
        if not payment_record:
            logger.warning(f"Midtrans payment record not found: {order_id}")
            return {"status": "ok", "reason": "payment_not_found"}

        chat_id = payment_record.get("chat_id")
        tier = payment_record.get("tier") or infer_tier_from_amount(int(gross_amount))
        username = payment_record.get("username", "")

        if not chat_id:
            logger.warning(f"Midtrans payment missing chat_id: {order_id}")
            return {"status": "ok", "reason": "missing_chat_id"}

        # Upgrade user tier
        from src.database import db
        from src.models import UserTier

        user = db.get_user(chat_id)
        if not user:
            logger.warning(f"User not found: chat_id={chat_id}")
            return {"status": "ok", "reason": "user_not_found"}

        old_tier = user.tier
        user.tier = UserTier[tier.upper()]
        user.tier_expires_at = None if tier == "lifetime" else None  # TODO: Add expiry for monthly
        db.upsert_user(user)
        logger.info(f"User upgraded: chat_id={chat_id}, {old_tier.value} → {tier}")

        # Send Telegram notification
        try:
            from src.bot.telegram import bot
            tier_emoji = {"pro": "💎", "premium": "👑", "lifetime": "🌟"}.get(tier, "✅")
            message = (
                f"{tier_emoji} *Pembayaran Berhasil!*\n\n"
                f"Tier kamu sekarang: *{tier.upper()}*\n"
                f"Order ID: `{order_id}`\n\n"
                f"Selamat trading! 🚀"
            )
            bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
            logger.info(f"Telegram notification sent: chat_id={chat_id}")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    except Exception as e:
        logger.error(f"Midtrans auto-upgrade failed: {e}")
        return {"status": "error", "reason": str(e)}

    return {"status": "ok", "order_id": order_id}


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

    # Accept more event types including Subscription Activated
    if event_name not in ("payment.paid", "payment.success", "order.paid",
                          "checkout.completed", "paid", "subscription activated",
                          "subscription.activated"):
        return {"status": "ignored", "event": event_name}

    # Extract metadata first (new API flow with ScaleV Business API)
    metadata = {}
    if isinstance(payload.get("data"), dict):
        metadata = payload["data"].get("metadata", {}) or {}
    if not metadata:
        metadata = payload.get("metadata", {}) or {}

    reference = extract_reference(event)
    if reference:
        mark_paid(reference)
        logger.info(f"Scalev payment marked paid: ref={reference}")

    # ── Auto-upgrade user tier + send Telegram notification + CAPI ──
    try:
        user_id = None
        tier = None
        amount = 0


        # Extract amount from webhook data
        webhook_data = payload.get("data", payload) if isinstance(payload.get("data"), dict) else payload
        amount = int(webhook_data.get("amount", webhook_data.get("gross_amount", 0)) or 0)

        # Try metadata first (new API flow)
        if metadata:
            user_id = metadata.get("chat_id") or metadata.get("telegram_username")
            tier = metadata.get("tier")
        # Fallback: look up in payments.json (old flow)
        if not user_id:
            from src.services.scalev import _load_payments, infer_tier_from_amount, normalize_amount
            payments_data = _load_payments()
            entry = payments_data.get("payments", {}).get(reference, {})
            user_id = entry.get("user_id")
            tier = tier or entry.get("tier") or infer_tier_from_amount(normalize_amount(entry.get("amount", 0)))

        if user_id and tier:
            from src.config import settings
            import sqlite3
            from datetime import datetime, timedelta, timezone

            db_path = settings.database_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.path.expanduser("~"), "projects", "idx-trading-bot", db_path)

            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row

                # Check if user exists
                user_row = conn.execute("SELECT id FROM users WHERE telegram_id=?", [int(user_id)]).fetchone()
                if not user_row:
                    # Create user
                    conn.execute(
                        "INSERT INTO users (telegram_id, username, created_at, last_active, is_active) VALUES (?, ?, ?, ?, 1)",
                        [int(user_id), f"user_{user_id}", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()]
                    )
                    conn.commit()
                    user_row = conn.execute("SELECT id FROM users WHERE telegram_id=?", [int(user_id)]).fetchone()
                    logger.info(f"Created new user: telegram_id={user_id}")

                user_db_id = user_row["id"] if user_row else None
                if user_db_id:
                    # Upsert subscription
                    existing = conn.execute("SELECT id FROM subscriptions WHERE user_id=?", [user_db_id]).fetchone()
                    expiry = None if tier == "lifetime" else (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                    if existing:
                        conn.execute("UPDATE subscriptions SET tier=?, start_date=?, end_date=?, payment_status='paid' WHERE user_id=?",
                                     [tier, datetime.now(timezone.utc).isoformat(), expiry, user_db_id])
                    else:
                        conn.execute("INSERT INTO subscriptions (user_id, tier, start_date, end_date, payment_status) VALUES (?, ?, ?, ?, 'paid')",
                                     [user_db_id, tier, datetime.now(timezone.utc).isoformat(), expiry])
                    conn.commit()
                    logger.info(f"✅ Auto-upgrade user={user_id} tier={tier}")
                    # ── Meta CAPI: Purchase ──
                    try:
                        from src.meta_capi import track_purchase
                        track_purchase(str(user_id), tier, value=float(amount), order_ref=reference)
                    except Exception:
                        pass
                conn.close()
            except Exception as e:
                logger.error(f"Auto-upgrade DB failed: {e}")

            # ── Fire Meta CAPI Purchase event ──
            try:
                import urllib.request
                META_PIXEL_ID = os.getenv("META_PIXEL_ID", "")
                META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
                if META_PIXEL_ID and META_ACCESS_TOKEN:
                    import hashlib
                    import time as _time
                    capi_event = {
                        "event_name": "Purchase",
                        "event_time": int(_time.time()),
                        "action_source": "other",
                        "event_id": f"idx_{user_id}_{tier}_{int(_time.time())}",
                        "custom_data": {
                            "currency": "IDR",
                            "value": amount / 1_000_000.0,
                            "content_name": f"Vilona Saham {tier.upper()}",
                            "content_category": "subscription",
                        },
                        "user_data": {
                            "external_id": hashlib.sha256(str(user_id).encode()).hexdigest(),
                        },
                    }
                    capi_payload = json.dumps({"data": [capi_event]}).encode()
                    capi_url = f"https://graph.facebook.com/v19.0/{META_PIXEL_ID}/events?access_token={META_ACCESS_TOKEN}"
                    capi_req = urllib.request.Request(capi_url, data=capi_payload, method="POST")
                    capi_req.add_header("Content-Type", "application/json")
                    with urllib.request.urlopen(capi_req, timeout=10) as r:
                        capi_result = json.loads(r.read())
                    logger.info(f"📊 Meta CAPI Purchase fired: {capi_result.get('events_received', 0)} events")
            except Exception as e:
                logger.warning(f"Meta CAPI error (non-fatal): {e}")

            # Send Telegram notification
            try:
                from telegram import Bot
                bot = Bot(token=settings.bot_token)
                tier_emoji = {"pro": "💎", "premium": "👑", "lifetime": "🌟"}.get(tier, "✅")
                tier_label = tier.upper()

                # Message 1: Welcome
                msg1 = (
                    f"{tier_emoji} *Pembayaran Berhasil!*\n\n"
                    f"Tier: *{tier_label}*\n"
                    f"Semua fitur premium udah aktif! 🚀"
                )

                # Message 2: Quick Start
                msg2 = (
                    f"📖 *Quick Start — Langsung Analisa!*\n"
                    f"━━━━━━━━━━━━━━━━\n\n"
                    f"1️⃣ Ketik nama saham:\n"
                    f"   `analisa BBCA`\n\n"
                    f"2️⃣ Lihat signal aktif:\n"
                    f"   `/signal`\n\n"
                    f"3️⃣ Screening saham:\n"
                    f"   `/screener momentum`\n\n"
                    f"4️⃣ Cek bandar flow:\n"
                    f"   `/bandarmologi BBCA`\n\n"
                    f"💡 Semua command: `/help`"
                )

                # Message 3: Features
                features = f"⭐ *Fitur {tier_label} Aktif:*\n"
                features += "✅ Unlimited screening 700+ saham\n"
                features += "✅ Signal Swing + Scalping\n"
                features += "✅ TP/SL otomatis\n"
                if tier in ("premium", "lifetime"):
                    features += "✅ Bandarmologi (deteksi bandar)\n"
                    features += "✅ Foreign Flow\n"
                    features += "✅ Sector Forecast\n"
                if tier == "lifetime":
                    features += "✅ Akses SELAMANYA\n"
                features += "\n📊 Cek status: `/status`"

                # Send all messages
                for msg in [msg1, msg2, features]:
                    try:
                        await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.warning(f"Telegram notification failed: {e}")
            except Exception as e:
                logger.warning(f"Telegram upgrade notification failed: {e}")
        else:
            logger.warning(f"Cannot auto-upgrade: user_id={user_id} tier={tier}")
    except Exception as e:
        logger.error(f"Auto-upgrade flow failed: {e}")


@router.post("/payments/notify")
async def scalev_notify_alias(request: Request):
    return await scalev_notify(request)


@router.post("/finnhub")
async def finnhub_webhook(request: Request):
    """Finnhub webhook endpoint for real-time market data."""
    import os
    secret = os.environ.get("finnhub_webhook_secret", "")
    
    try:
        body = await request.body()
        payload = await request.json()
        
        # Verify secret if provided
        if secret:
            auth = request.headers.get("X-Finnhub-Secret", "")
            if auth != secret:
                return JSONResponse({"error": "Invalid secret"}, status_code=401)
        
        # Process Finnhub data
        event_type = payload.get("type", "")
        data = payload.get("data", {})
        
        logger.info(f"Finnhub webhook: {event_type} - {data}")
        
        # Save to database or process
        # TODO: Integrate with signal engine
        
        return JSONResponse({"status": "ok", "type": event_type})
    except Exception as e:
        logger.error(f"Finnhub webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
