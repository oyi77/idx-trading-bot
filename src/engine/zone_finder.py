"""Zone mapping — support, resistance, entry zone from OHLCV data."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ZoneFinder:
    """Calculate support / resistance / entry zones from price action."""

    def find_levels(self, klines: list[dict], current_price: float) -> dict:
        """Find key support & resistance levels.

        Args:
            klines: list of {open, high, low, close, volume}
            current_price: latest close

        Returns:
            {
                "support": price,
                "resistance": price,
                "strong_support": price,
                "strong_resistance": price,
                "entry_zone_low": price,
                "entry_zone_high": price,
                "pivot_lows": [price, ...],
                "pivot_highs": [price, ...],
            }
        """
        if not klines:
            return self._empty()

        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]

        # ── Pivot highs (resistance candidates) ──
        pivot_highs = []
        for i in range(2, len(highs) - 2):
            if (
                highs[i] > highs[i - 1]
                and highs[i] > highs[i - 2]
                and highs[i] >= highs[i + 1]
                and highs[i] >= highs[i + 2]
            ):
                pivot_highs.append(highs[i])

        # ── Pivot lows (support candidates) ──
        pivot_lows = []
        for i in range(2, len(lows) - 2):
            if (
                lows[i] < lows[i - 1]
                and lows[i] < lows[i - 2]
                and lows[i] <= lows[i + 1]
                and lows[i] <= lows[i + 2]
            ):
                pivot_lows.append(lows[i])

        # ── Nearest R above price ──
        resistance = None
        strong_resistance = None
        above = [h for h in pivot_highs if h > current_price]
        if above:
            above.sort()
            resistance = above[0]
            if len(above) > 1:
                strong_resistance = above[-1]

        # ── Nearest S below price ──
        support = None
        strong_support = None
        below = [l for l in pivot_lows if l < current_price]
        if below:
            below.sort(reverse=True)
            support = below[0]
            if len(below) > 1:
                strong_support = below[-1]

        # Fallback: use min/max
        if not support:
            support = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        if not resistance:
            resistance = max(highs[-20:]) if len(highs) >= 20 else max(highs)

        # ── Entry zone (tight range around price) ──
        entry_zone_low = current_price * 0.995
        entry_zone_high = current_price * 1.005

        return {
            "support": round(support, 0),
            "resistance": round(resistance, 0),
            "strong_support": round(strong_support, 0) if strong_support else None,
            "strong_resistance": round(strong_resistance, 0) if strong_resistance else None,
            "entry_zone_low": round(entry_zone_low, 0),
            "entry_zone_high": round(entry_zone_high, 0),
            "pivot_highs": [round(h, 0) for h in pivot_highs[-5:]],
            "pivot_lows": [round(l, 0) for l in pivot_lows[-5:]],
        }

    def _empty(self) -> dict:
        return {
            "support": 0,
            "resistance": 0,
            "strong_support": None,
            "strong_resistance": None,
            "entry_zone_low": 0,
            "entry_zone_high": 0,
            "pivot_highs": [],
            "pivot_lows": [],
        }
