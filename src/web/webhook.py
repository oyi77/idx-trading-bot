"""Finnhub webhook handler — receives real-time data pushes."""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["webhook"])

# Store last received data for debugging
_last_data: dict = {}
_last_received: Optional[datetime] = None


@router.post("/webhook")
async def finnhub_webhook_root(request: Request):
    """Accept webhook at /webhook path."""
    return await finnhub_webhook_inner(request)


@router.post("/webhook/finnhub")
async def finnhub_webhook(request: Request):
    """Receive real-time data from Finnhub webhook."""
    return await finnhub_webhook_inner(request)


async def finnhub_webhook_inner(request: Request):
    """Shared webhook logic."""
    global _last_data, _last_received

    try:
        body = await request.json()
    except Exception:
        body = await request.body()
        try:
            body = json.loads(body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    _last_data = body
    _last_received = datetime.now()

    logger.info(f"📡 Finnhub webhook received: type={body.get('type', 'unknown')}")

    # Handle different Finnhub webhook types
    event_type = body.get("type", "")

    if event_type == "trade":
        # Real-time trade data
        data = body.get("data", [])
        for trade in data:
            symbol = trade.get("s", "")
            price = trade.get("p", 0)
            volume = trade.get("v", 0)
            timestamp = trade.get("t", 0)
            logger.info(f"   Trade: {symbol} @ {price} vol={volume}")

    elif event_type == "quote":
        # Quote update
        symbol = body.get("s", "")
        price = body.get("p", 0)
        change = body.get("c", 0)
        logger.info(f"   Quote: {symbol} @ {price} ({change:+.2f}%)")

    elif event_type == "news":
        # News event
        headline = body.get("headline", "")
        summary = body.get("summary", "")[:100]
        logger.info(f"   News: {headline} — {summary}...")

    elif event_type == "candle":
        # Candle close
        symbol = body.get("s", "")
        close = body.get("c", 0)
        volume = body.get("v", 0)
        logger.info(f"   Candle: {symbol} close={close} vol={volume}")

    else:
        logger.info(f"   Unknown event type: {event_type}")
        logger.info(f"   Raw: {json.dumps(body)[:500]}")

    return {"status": "ok", "received_at": _last_received.isoformat()}


@router.get("/webhook/finnhub")
async def finnhub_verify(request: Request):
    """Finnhub webhook verification endpoint (GET)."""
    # Finnhub sometimes sends GET to verify webhook URL
    challenge = request.query_params.get("challenge", "")
    logger.info(f"📡 Finnhub verification: challenge={challenge}")

    if challenge:
        return {"challenge": challenge}
    return {"status": "ok", "message": "Finnhub webhook endpoint active"}


@router.get("/webhook/finnhub/last")
async def finnhub_last_data():
    """Return the last received webhook payload (debug endpoint)."""
    global _last_data, _last_received
    return {
        "last_received": _last_received.isoformat() if _last_received else None,
        "data": _last_data,
    }


@router.get("/webhook/finnhub/health")
async def finnhub_health():
    """Health check for Finnhub webhook."""
    return {
        "status": "ok",
        "endpoint": "/webhook/finnhub",
        "last_received": _last_received.isoformat() if _last_received else None,
        "service": "IDX AI Trading Bot — Finnhub Webhook",
    }
