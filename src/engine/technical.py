"""
Technical analysis engine for IDX stocks.
Wraps indicator_defs into higher-level screening + analysis functions.
"""
from typing import Dict, List, Optional, Tuple

from src.engine.indicator_defs import (
    MACDResult,
    bollinger,
    ema,
    macd,
    rsi,
    rsi_signal,
    sma,
    supertrend,
    volume_spike,
    vwap,
)


class TechnicalEngine:
    """Run technical analysis on OHLCV data."""

    def analyze(
        self, symbol: str, closes: List[float], highs: List[float],
        lows: List[float], volumes: List[int]
    ) -> Dict:
        """Run all indicators, return structured result."""
        if not closes:
            return {"symbol": symbol, "error": "No data"}

        current_price = closes[-1]
        results = {"symbol": symbol, "price": current_price, "indicators": {}}

        # ── Moving Averages ──
        for period in [5, 10, 20, 50, 200]:
            if len(closes) >= period:
                ma = sma(closes, period)
                results["indicators"][f"SMA{period}"] = round(ma[-1], 2) if ma else None

        # EMA 20 cross check
        if len(closes) >= 20:
            ma20 = sma(closes, 20)
            ema20 = ema(closes, 20)
            cross = "above" if ema20[-1] > ma20[-1] else "below"
            results["indicators"]["EMA20_MA20_cross"] = cross

        # ── RSI ──
        rsi_val = rsi(closes)
        results["indicators"]["RSI14"] = round(rsi_val, 2)
        results["indicators"]["RSI_signal"] = rsi_signal(rsi_val).signal

        # ── MACD ──
        macd_result = macd(closes)
        if macd_result:
            results["indicators"]["MACD"] = {
                "macd": round(macd_result.macd, 2),
                "signal": round(macd_result.signal, 2),
                "histogram": round(macd_result.histogram, 2),
                "trend": macd_result.trend,
            }

        # ── Bollinger ──
        bb = bollinger(closes)
        if bb:
            results["indicators"]["Bollinger"] = {
                "upper": round(bb.upper, 2),
                "middle": round(bb.middle, 2),
                "lower": round(bb.lower, 2),
                "position": bb.position,
            }

        # ── SuperTrend ──
        if len(highs) >= 10 and len(lows) >= 10:
            st = supertrend(highs, lows, closes)
            results["indicators"]["SuperTrend"] = {
                "trend": st.trend,
                "line": round(st.line, 2),
            }

        # ── Volume ──
        if volumes:
            results["indicators"]["Volume"] = {
                "latest": volumes[-1],
                "spike": volume_spike(volumes),
                "avg_20": round(sum(volumes[-20:]) / min(20, len(volumes))),
            }

        # ── VWAP ──
        if len(highs) >= 10 and volumes:
            vwap_val = vwap(highs, lows, closes, volumes)
            if vwap_val:
                results["indicators"]["VWAP"] = round(vwap_val, 2)
                results["indicators"]["VWAP_position"] = "above" if current_price > vwap_val else "below"

        return results

    def combined_score(
        self, closes: List[float], highs: List[float],
        lows: List[float], volumes: List[int]
    ) -> Tuple[int, List[str]]:
        """Score 0-10: bullish signals count."""
        score = 0
        reasons = []

        # RSI
        rsi_val = rsi(closes)
        if rsi_val < 30:
            score += 2
            reasons.append("Oversold")
        elif rsi_val > 70:
            score -= 1
            reasons.append("Overbought")
        else:
            score += 1
            reasons.append("RSI normal")

        # MACD
        macd_result = macd(closes)
        if macd_result and macd_result.trend == "bullish":
            score += 2
            reasons.append("MACD bullish")

        # Price above SMA20
        if len(closes) >= 20:
            sma20 = sma(closes, 20)
            if sma20 and closes[-1] > sma20[-1]:
                score += 1
                reasons.append("Above SMA20")

        # Volume spike
        if volume_spike(volumes):
            score += 1
            reasons.append("Volume spike")

        # SuperTrend
        if len(highs) >= 10:
            st = supertrend(highs, lows, closes)
            if st.trend == "bullish":
                score += 2
                reasons.append("SuperTrend bullish")
            elif st.trend == "bearish":
                score -= 1
                reasons.append("SuperTrend bearish")

        # Bollinger position
        bb = bollinger(closes)
        if bb and bb.position == "above":
            score += 1
            reasons.append("Price above Bollinger upper")

        return max(0, min(10, score)), reasons
