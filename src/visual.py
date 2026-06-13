"""TradingView chart rendering via chart-img.com — clean, no overlay."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from src.engine.chart_img import snapshot as tv_snapshot

DEFAULT_STUDIES = ["Volume", "MACD"]


async def download_chart(symbol: str, **kwargs) -> Optional[Path]:
    """Download a clean TradingView chart image. Returns path or None."""
    png_bytes = await tv_snapshot(symbol, **kwargs)
    if not png_bytes:
        return None
    out = Path(f"/tmp/chart_{symbol}.png")
    out.write_bytes(png_bytes)
    return out
