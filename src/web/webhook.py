"""FastAPI webhook endpoint for Tripay payment callback.
Deployed via the existing web server on port 8083.
"""
import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/tripay")
async def tripay_callback(request: Request):
    """Receive Tripay payment notification. Auto-upgrade user on success."""
    try:
        body = await request.body()
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Verify signature
    callback_sig = request.headers.get("X-Callback-Signature", "")
    if callback_sig:
        from src.services.payment import verify_callback, TRIPAY_PRIVATE_KEY
        raw = json.dumps(payload, separators=(",", ":"))
        if not verify_callback(raw, callback_sig):
            logger.warning(f"Invalid Tripay signature for {payload.get('merchant_ref')}")
            raise HTTPException(status_code=403, detail="Invalid signature")

    from src.services.payment import handle_callback
    result = handle_callback(payload)

    logger.info(f"Webhook processed: {result}")
    return {"status": "ok", "detail": result}
