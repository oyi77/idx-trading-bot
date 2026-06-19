"""Signal Engine — Generates trading signals with TP/SL for Swing & Scalping.

Uses existing screener_cache + indicator_defs to produce actionable signals.

Swing Trade:
  - Duration: 3-14 hari
  - TP: multi-level (TP1, TP2, TP3)
  - SL: below support / below entry zone
  - Indicators: MA cross, RSI, MACD, S/R levels, volume trend

Scalping:
  - Duration: intraday – 2 hari
  - TP: quick target 1-3%
  - SL: tight stop 0.5-1.5%
  - Indicators: VWAP, short MA, volume spike, RSI momentum
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from src.engine.indicator_defs import (
    bollinger, ema, macd, rsi, sma, supertrend, volume_spike, vwap,
)


@dataclass
class TradeSignal:
    """Single actionable trading signal."""
    symbol: str
    signal_type: str          # "swing" | "scalp"
    direction: str            # "LONG" | "SHORT"
    entry_price: float        # recommended entry
    entry_low: float          # entry zone low
    entry_high: float         # entry zone high
    tp1: float                # take profit 1
    tp2: float                # take profit 2
    tp3: Optional[float]      # take profit 3 (swing only)
    sl: float                 # stop loss
    rr_ratio: float           # risk:reward
    confidence: int           # 0-100
    timeframe: str            # "1-2 hari" | "3-7 hari" | "7-14 hari"
    reasons: List[str] = field(default_factory=list)
    indicators: Dict[str, float] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%d %b %Y %H:%M"))


@dataclass
class SignalBatch:
    """Batch of signals for one type."""
    signal_type: str
    description: str
    signals: List[TradeSignal] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%d %b %Y %H:%M"))


# ── Support/Resistance Calculator ──────────────────────────────

def _find_support_resistance(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    window: int = 20,
) -> Dict[str, List[float]]:
    """Find S/R levels from recent price action using pivot points."""
    supports: List[float] = []
    resistances: List[float] = []

    for i in range(window, len(lows) - window):
        if lows[i] == min(lows[i - window:i + window + 1]):
            supports.append(lows[i])
        if highs[i] == max(highs[i - window:i + window + 1]):
            resistances.append(highs[i])

    def cluster(levels: List[float], pct: float = 0.015) -> List[float]:
        if not levels:
            return []
        levels.sort()
        clustered = [levels[0]]
        for lv in levels[1:]:
            if abs(lv - clustered[-1]) / clustered[-1] > pct:
                clustered.append(lv)
            else:
                clustered[-1] = (clustered[-1] + lv) / 2
        return clustered

    return {
        "supports": cluster(supports)[-5:],
        "resistances": cluster(resistances)[:5],
    }


def _calc_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Average True Range for dynamic SL/TP sizing."""
    if len(closes) < period + 1:
        return (highs[-1] - lows[-1]) if highs and lows else 0.0

    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs[-period:]) / period


# ── Swing Signal Generator ─────────────────────────────────────

def generate_swing_signals(
    symbol: str,
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[int],
    max_signals: int = 1,
) -> List[TradeSignal]:
    """Generate swing trade signals (3-14 hari).

    Entry logic:
    - RSI 30-50 + MACD bullish cross = BUY zone
    - Price near support + MA golden cross = BUY zone
    - Supertrend bullish = confirmation
    """
    if len(closes) < 50:
        return []

    price = closes[-1]

    # ── Indicators ──
    rsi_val = rsi(closes, 14)
    macd_result = macd(closes)
    sma20_list = sma(closes, 20)
    sma50_list = sma(closes, 50)
    ema9_list = ema(closes, 9)
    st_result = supertrend(closes, highs, lows)
    atr_val = _calc_atr(highs, lows, closes, 14)
    sr = _find_support_resistance(closes, highs, lows, window=10)

    if not sma20_list or not sma50_list or not ema9_list:
        return []

    current_sma20 = sma20_list[-1]
    current_sma50 = sma50_list[-1]
    current_ema9 = ema9_list[-1]

    # ── Scoring ──
    score = 0
    reasons: List[str] = []

    # 1. RSI zone
    if 30 <= rsi_val <= 55:
        score += 20
        reasons.append(f"RSI {rsi_val:.1f} — zona akumulasi")
    elif rsi_val < 30:
        score += 15
        reasons.append(f"RSI {rsi_val:.1f} — oversold, potensi reversal")

    # 2. MACD bullish
    if macd_result and macd_result.histogram > 0:
        score += 15
        reasons.append("MACD histogram positif")
    if macd_result and macd_result.trend == "bullish":
        score += 10
        reasons.append("MACD trend bullish")

    # 3. MA structure
    if current_sma20 > current_sma50:
        score += 15
        reasons.append("SMA20 > SMA50 — struktur bullish")
    if price > current_sma20:
        score += 10
        reasons.append(f"Harga di atas SMA20 ({current_sma20:.0f})")

    # 4. Supertrend
    if st_result and st_result.trend == "bullish":
        score += 15
        reasons.append("Supertrend bullish")

    # 5. Near support
    nearest_support: Optional[float] = None
    for s in reversed(sr["supports"]):
        if s < price:
            nearest_support = s
            break
    if nearest_support and (price - nearest_support) / price < 0.03:
        score += 10
        reasons.append(f"Dekat support ({nearest_support:.0f})")

    # 6. Volume confirmation
    if volumes and len(volumes) >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        if volumes[-1] > avg_vol * 1.3:
            score += 5
            reasons.append("Volume di atas rata-rata")

    # ── Generate signal if score >= 50 ──
    if score < 50:
        return []

    # ── Calculate TP/SL using ATR ──
    entry = price
    entry_low = round(price - atr_val * 0.3, 2)
    entry_high = round(price + atr_val * 0.3, 2)

    tp1 = round(price + atr_val * 1.5, 2)
    tp2 = round(price + atr_val * 2.5, 2)
    tp3 = round(price + atr_val * 4.0, 2)

    if nearest_support and nearest_support < price:
        sl = round(min(nearest_support * 0.99, price - atr_val * 1.5), 2)
    else:
        sl = round(price - atr_val * 1.5, 2)

    risk = price - sl
    reward = tp2 - price
    rr = round(reward / risk, 2) if risk > 0 else 0.0

    confidence = min(score, 100)
    timeframe = "7-14 hari" if score >= 75 else "3-7 hari"

    indicators: Dict[str, float] = {
        "RSI": round(rsi_val, 2),
        "SMA20": round(current_sma20, 2),
        "SMA50": round(current_sma50, 2),
        "ATR": round(atr_val, 2),
    }
    if macd_result:
        indicators["MACD_hist"] = round(macd_result.histogram, 4)
    if st_result:
        indicators["Supertrend_line"] = round(st_result.line, 2)

    return [TradeSignal(
        symbol=symbol,
        signal_type="swing",
        direction="LONG",
        entry_price=round(entry, 2),
        entry_low=entry_low,
        entry_high=entry_high,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        sl=sl,
        rr_ratio=rr,
        confidence=confidence,
        timeframe=timeframe,
        reasons=reasons,
        indicators=indicators,
    )][:max_signals]


# ── Scalping Signal Generator ──────────────────────────────────

def generate_scalp_signals(
    symbol: str,
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[int],
    max_signals: int = 1,
) -> List[TradeSignal]:
    """Generate scalping signals (intraday – 2 hari).

    Entry logic:
    - RSI 40-60 + momentum up = quick entry
    - Price above VWAP + volume spike = confirmation
    - EMA9 > EMA20 = short-term bullish
    - Bollinger lower band bounce = entry zone
    """
    if len(closes) < 20:
        return []

    price = closes[-1]

    # ── Indicators ──
    rsi_val = rsi(closes, 7)
    ema9_list = ema(closes, 9)
    ema20_list = ema(closes, 20)
    bb = bollinger(closes, 20, 2)
    atr_val = _calc_atr(highs, lows, closes, 7)
    has_vol_spike = volume_spike(volumes, 10)

    # VWAP approximation
    if volumes and len(volumes) >= 10:
        typical_prices = [(closes[i] + highs[i] + lows[i]) / 3 for i in range(-10, 0)]
        vol_recent = volumes[-10:]
        cum_tp_vol = sum(p * v for p, v in zip(typical_prices, vol_recent))
        cum_vol = sum(vol_recent)
        vwap_val = cum_tp_vol / cum_vol if cum_vol > 0 else price
    else:
        vwap_val = price

    if not ema9_list or not ema20_list or not bb:
        return []

    current_ema9 = ema9_list[-1]
    current_ema20 = ema20_list[-1]

    # ── Scoring ──
    score = 0
    reasons: List[str] = []

    # 1. RSI momentum zone
    if 40 <= rsi_val <= 65:
        score += 20
        reasons.append(f"RSI {rsi_val:.1f} — momentum netral-bullish")
    elif rsi_val < 35:
        score += 15
        reasons.append(f"RSI {rsi_val:.1f} — oversold bounce potential")

    # 2. EMA cross
    if current_ema9 > current_ema20:
        score += 20
        reasons.append("EMA9 > EMA20 — momentum naik")

    # 3. Price vs VWAP
    if price > vwap_val:
        score += 15
        reasons.append(f"Harga di atas VWAP ({vwap_val:.0f})")

    # 4. Bollinger position
    if price <= bb.lower * 1.01:
        score += 15
        reasons.append("Dekat lower Bollinger — bounce potential")
    elif price < bb.middle:
        score += 10
        reasons.append("Di bawah middle Bollinger")

    bb_width = (bb.upper - bb.lower) / bb.middle if bb.middle > 0 else 0
    if bb_width < 0.04:
        score += 5
        reasons.append("Bollinger squeeze — siap breakout")

    # 5. Volume spike
    if has_vol_spike:
        score += 15
        reasons.append("Volume spike detected")

    # 6. Recent momentum
    if len(closes) >= 4:
        recent_change = (closes[-1] - closes[-4]) / closes[-4] * 100
        if 0.5 <= recent_change <= 3:
            score += 10
            reasons.append(f"Momentum +{recent_change:.1f}% (3 candle)")

    # ── Generate signal if score >= 55 ──
    if score < 55:
        return []

    # ── Calculate TP/SL (tight for scalping) ──
    entry = price
    entry_low = round(price - atr_val * 0.2, 2)
    entry_high = round(price + atr_val * 0.2, 2)

    tp1 = round(price + atr_val * 1.0, 2)
    tp2 = round(price + atr_val * 2.0, 2)

    sl = round(price - atr_val * 0.8, 2)

    risk = price - sl
    reward = tp1 - price
    rr = round(reward / risk, 2) if risk > 0 else 0.0

    confidence = min(score, 100)
    timeframe = "intraday – 2 hari"

    indicators: Dict[str, float] = {
        "RSI7": round(rsi_val, 2),
        "EMA9": round(current_ema9, 2),
        "EMA20": round(current_ema20, 2),
        "VWAP": round(vwap_val, 2),
        "ATR7": round(atr_val, 2),
        "BB_lower": round(bb.lower, 2),
        "BB_upper": round(bb.upper, 2),
    }

    return [TradeSignal(
        symbol=symbol,
        signal_type="scalp",
        direction="LONG",
        entry_price=round(entry, 2),
        entry_low=entry_low,
        entry_high=entry_high,
        tp1=tp1,
        tp2=tp2,
        tp3=None,
        sl=sl,
        rr_ratio=rr,
        confidence=confidence,
        timeframe=timeframe,
        reasons=reasons,
        indicators=indicators,
    )][:max_signals]


# ── Batch Scanner ──────────────────────────────────────────────

async def scan_signals(
    signal_type: str = "swing",
    symbols: Optional[List[str]] = None,
    limit: int = 5,
) -> SignalBatch:
    """Scan all stocks for swing or scalp signals.

    Args:
        signal_type: "swing" or "scalp"
        symbols: specific symbols to scan (default: full IDX universe)
        limit: max signals to return

    Returns:
        SignalBatch with top signals sorted by confidence.
    """
    from src.engine.screener_cache import fetch_all_cached

    if signal_type not in ("swing", "scalp"):
        return SignalBatch(signal_type=signal_type, description="Invalid signal type")

    data = await fetch_all_cached()
    if not data:
        return SignalBatch(
            signal_type=signal_type,
            description="Data tidak tersedia. Market mungkin belum buka.",
        )

    all_signals: List[TradeSignal] = []
    gen_func = generate_swing_signals if signal_type == "swing" else generate_scalp_signals

    target_symbols = symbols or list(data.keys())

    for sym in target_symbols:
        stock = data.get(sym)
        if not stock:
            continue

        closes = stock.get("closes", [])
        highs = stock.get("highs", [])
        lows = stock.get("lows", [])
        volumes = stock.get("volumes", [])

        if len(closes) < 20:
            continue

        try:
            sigs = gen_func(sym, closes, highs, lows, volumes, max_signals=1)
            all_signals.extend(sigs)
        except Exception:
            continue

    all_signals.sort(key=lambda s: (s.confidence, s.rr_ratio), reverse=True)
    top_signals = all_signals[:limit]

    desc_map = {
        "swing": "Swing Trade (3-14 hari)",
        "scalp": "Scalping (intraday – 2 hari)",
    }

    return SignalBatch(
        signal_type=signal_type,
        description=desc_map.get(signal_type, signal_type),
        signals=top_signals,
    )
