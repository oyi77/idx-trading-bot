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
    return {"status": "ok", "reference": reference}


@router.post("/payments/notify")
async def scalev_notify_alias(request: Request):
    return await scalev_notify(request)
