"""TradingView chart rendering via chart-img.com (async, streaming PNG)."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CHART_IMG_V2 = "https://api.chart-img.com/v2/tradingview/advanced-chart"


def _get_chart_img_key() -> str:
    """Read CHART_IMG_API_KEY from environment or .env file."""
    key = os.getenv("CHART_IMG_API_KEY", "")
    if key:
        return key
    env_path = Path.home() / ".idx-trading-bot" / ".env"
    if not env_path.exists():
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("CHART_IMG_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


async def snapshot(
    symbol: str,
    *,
    market: str = "IDX",
    interval: str = "1D",
    theme: str = "dark",
    studies: Optional[list[str]] = None,
) -> Optional[bytes]:
    """Fetch a TradingView chart PNG as raw bytes via chart-img v2 API."""
    try:
        import httpx

        key = _get_chart_img_key()
        if not key:
            logger.warning("CHART_IMG_API_KEY not set")
            return None

        if ":" not in symbol:
            tv_symbol = f"{market}:{symbol}"
        else:
            tv_symbol = symbol

        payload = {
            "symbol": tv_symbol,
            "interval": interval,
            "theme": theme,
            "width": 800,
            "height": 450,
        }
        if studies:
            # Volume, MACD, RSI, Stochastic = pane bawah
            # SMA, EMA, Bollinger, VWAP = overlay di chart utama
            overlay_set = {"SMA", "EMA", "Bollinger", "BB", "VWAP"}
            payload["studies"] = [
                {"name": s, "forceOverlay": s in overlay_set}
                for s in studies
            ]

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.post(
                CHART_IMG_V2,
                headers={
                    "x-api-key": key,
                    "content-type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 429:
                logger.warning("chart-img rate limit reached")
                return None
            if resp.status_code in (401, 403):
                logger.warning(f"chart-img auth failed: {resp.status_code}")
                return None
            if resp.status_code == 422:
                logger.warning(f"chart-img bad params: {resp.text[:200]}")
                return None
            if resp.status_code != 200:
                logger.warning(f"chart-img returned {resp.status_code}: {resp.text[:200]}")
                return None

            if resp.content[:4] == b"\x89PNG":
                return resp.content

            logger.warning("chart-img returned non-PNG content")
            return None

    except ImportError:
        logger.warning("httpx not installed — pip install httpx")
        return None
    except Exception as exc:
        logger.warning(f"chart-img fetch error: {exc}")
        return None
