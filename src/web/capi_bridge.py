"""CAPI bridge — sends events to Meta Conversions API using env-configured endpoint."""
import json
import logging
import os
import time

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

CAPI_URL = os.environ.get("META_CAPI_URL", "").strip()
CAPI_TOKEN = os.environ.get("META_CAPI_TOKEN", "").strip()
CAPI_PIXEL = os.environ.get("META_PIXEL_ID", "320653057513880").strip()


async def handle_capi(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "detail": "invalid json"}, status_code=400)

    event_name = body.get("event_name", "PageView")
    event_data = body.get("event_data", {})

    if not CAPI_URL or not CAPI_TOKEN:
        logger.info(f"CAPI skipped (not configured): {event_name}")
        return {"status": "skipped", "event": event_name}

    payload = {
        "data": [{
            "event_name": event_name,
            "event_time": int(time.time()),
            "action_source": "website",
            "event_source_url": body.get("source_url", ""),
            "user_data": {
                "client_ip_address": request.client.host if request.client else "",
                "client_user_agent": request.headers.get("user-agent", ""),
            },
            "custom_data": event_data if isinstance(event_data, dict) else {},
        }],
        "access_token": CAPI_TOKEN,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(CAPI_URL, json=payload)
        logger.info(f"CAPI: {event_name} -> {resp.status_code}")
        return {"status": "ok", "fb_status": resp.status_code}
    except Exception as e:
        logger.warning(f"CAPI send failed: {e}")
        return {"status": "error", "detail": str(e)}
