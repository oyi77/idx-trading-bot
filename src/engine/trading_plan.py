"""Auto Trading Plan Generator — Entry/SL/TP/RR dari SMC Structure.

Menganalisa struktur pasar (swing highs/lows), support/resistance,
dan ATR untuk auto-generate trading plan presisi ala Stockpick Signal.

Components:
  - Entry zone: current price ± buffer based on ATR
  - Stop Loss: recent swing low (long) / swing high (short)
  - TP1: first resistance (long) / first support (short)
  - TP2: second resistance / fibonacci extension
  - RR ratio: risk-reward calculation
  - Confidence score: 0-20 composite (trend + volume + structure + flow)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class TradingPlan:
    """Auto-generated trading plan for a stock."""
    symbol: str
    signal: str  # "BUY" / "SELL" / "HOLD"
    entry_min: float
    entry_max: float
    stop_loss: float
    sl_pct: float  # SL as % from entry
    tp1: float
    tp1_pct: float
    tp2: float
    tp2_pct: float
    rr_ratio: float  # Risk:Reward to TP1
    confidence: int  # 0-20
    grade: str  # "A" / "B" / "C" / "D"
    reasoning: List[str]  # Brief reasons for the plan
    vwap: float = 0
    vwap_pct: float = 0  # distance from entry to VWAP


class TradingPlanEngine:
    """Generate auto trading plans from price data + structure analysis."""

    ATR_PERIOD = 14
    ATR_SL_MULTIPLIER = 1.5   # SL = entry - (ATR * multiplier)
    ATR_TP1_MULTIPLIER = 2.0  # TP1 = entry + (ATR * multiplier)
    ATR_TP2_MULTIPLIER = 3.5  # TP2 = entry + (ATR * multiplier)
    ENTRY_BUFFER_PCT = 0.005   # 0.5% entry zone width

    def generate(
        self,
        symbol: str,
        current_price: float,
        ohlc_data: List[Dict],
        smc_trend: str = "",
        accumulation_score: int = 50,
        volume_ratio: float = 1.0,
    ) -> TradingPlan:
        """Generate a complete trading plan."""
        closes = np.array([c["close"] for c in ohlc_data[-60:]])
        highs = np.array([c["high"] for c in ohlc_data[-60:]])
        lows = np.array([c["low"] for c in ohlc_data[-60:]])
        volumes = np.array([float(c.get("volume", 0) or 0) for c in ohlc_data[-60:]])

        # 1. Calculate ATR
        atr = self._calculate_atr(highs, lows, closes)

        # 2. Find key levels
        support, resistance = self._find_sr_levels(highs, lows, closes)

        # 3. Determine signal direction
        signal = self._determine_signal(smc_trend, current_price, support, resistance)

        # 4. Generate plan based on direction
        if signal == "BUY":
            plan = self._generate_long_plan(
                symbol, current_price, atr, support, resistance, closes, volumes
            )
        elif signal == "SELL":
            plan = self._generate_short_plan(
                symbol, current_price, atr, support, resistance, closes, volumes
            )
        else:
            plan = self._generate_hold_plan(symbol, current_price, atr, support, resistance)

        # 5. Calculate confidence score
        plan.confidence = self._calculate_confidence(
            signal, smc_trend, accumulation_score, volume_ratio,
            plan.rr_ratio, closes
        )

        # 6. Assign grade
        plan.grade = self._assign_grade(plan.confidence, plan.rr_ratio)

        # 7. Calculate VWAP
        plan.vwap = self._calculate_vwap(ohlc_data[-20:])
        if plan.vwap > 0 and plan.entry_max > 0:
            plan.vwap_pct = (plan.entry_max / plan.vwap - 1) * 100

        return plan

    # ── ATR ──────────────────────────────────────────────────

    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> float:
        """Calculate Average True Range."""
        if len(closes) < 2:
            return closes[-1] * 0.02  # fallback 2%

        tr_list = []
        for i in range(1, min(len(closes), self.ATR_PERIOD + 5)):
            h_l = highs[i] - lows[i]
            h_pc = abs(highs[i] - closes[i - 1])
            l_pc = abs(lows[i] - closes[i - 1])
            tr_list.append(max(h_l, h_pc, l_pc))

        if tr_list:
            return float(np.mean(tr_list))
        return closes[-1] * 0.02

    # ── Support/Resistance ───────────────────────────────────

    def _find_sr_levels(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray
    ) -> Tuple[List[float], List[float]]:
        """Find key support and resistance levels from swing points."""
        supports = []
        resistances = []
        w = 5  # swing window

        # Find swing lows (support)
        for i in range(w, len(lows) - w):
            if all(lows[i] <= lows[i - j] for j in range(1, w + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, w + 1)):
                supports.append(float(lows[i]))

        # Find swing highs (resistance)
        for i in range(w, len(highs) - w):
            if all(highs[i] >= highs[i - j] for j in range(1, w + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, w + 1)):
                resistances.append(float(highs[i]))

        # Deduplicate and sort
        supports = sorted(set(round(s, 0) for s in supports))
        resistances = sorted(set(round(r, 0) for r in resistances), reverse=True)

        return supports[-5:] if supports else [], resistances[:5] if resistances else []

    # ── Signal ───────────────────────────────────────────────

    def _determine_signal(
        self, smc_trend: str, price: float,
        support: List[float], resistance: List[float]
    ) -> str:
        """Determine BUY/SELL/HOLD based on SMC trend and price position."""
        if smc_trend == "BULLISH":
            return "BUY"
        elif smc_trend == "BEARISH":
            return "SELL"

        # Neutral: check price position vs support/resistance
        if support and price <= support[0] * 1.02:
            return "BUY"  # near support
        if resistance and price >= resistance[-1] * 0.98:
            return "SELL"  # near resistance

        return "HOLD"

    # ── Long Plan (BUY) ──────────────────────────────────────

    def _generate_long_plan(
        self, symbol: str, price: float, atr: float,
        support: List[float], resistance: List[float],
        closes: np.ndarray, volumes: np.ndarray
    ) -> TradingPlan:
        """Generate BUY trading plan."""
        # Entry zone: current price with buffer
        buffer = price * self.ENTRY_BUFFER_PCT
        entry_min = price - buffer
        entry_max = price + buffer

        # Stop Loss: nearest support or ATR-based (capped at 8%)
        if support:
            candidates = [s for s in support if price * 0.92 < s < price * 0.98]
            nearest_support = max(candidates) if candidates else price - (atr * self.ATR_SL_MULTIPLIER)
        else:
            nearest_support = price - (atr * self.ATR_SL_MULTIPLIER)

        sl = max(nearest_support, price * 0.92)  # hard cap 8%
        sl_pct = (price - sl) / price * 100 if price > 0 else 0

        # Take Profit 1: nearest resistance or ATR-based
        if resistance:
            candidates = [r for r in resistance if r > price * 1.02]
            tp1 = min(candidates) if candidates else price + (atr * self.ATR_TP1_MULTIPLIER)
        else:
            tp1 = price + (atr * self.ATR_TP1_MULTIPLIER)

        tp1_pct = (tp1 - price) / price * 100

        # Take Profit 2: second resistance or fibonacci 1.618
        if resistance:
            candidates = [r for r in resistance if r > tp1 * 1.01]
            tp2 = min(candidates) if candidates else price + (atr * self.ATR_TP2_MULTIPLIER)
        else:
            # Fibonacci extension
            swing_low = min(closes[-20:]) if len(closes) >= 20 else price * 0.9
            swing_high = max(closes[-20:]) if len(closes) >= 20 else price * 1.1
            fib_ext = swing_high + (swing_high - swing_low) * 0.618
            tp2 = min(fib_ext, price + (atr * self.ATR_TP2_MULTIPLIER))

        tp2_pct = (tp2 - price) / price * 100

        # Risk-Reward Ratio
        risk = price - sl if price > sl else 0.01
        reward = tp1 - price
        rr = reward / risk if risk > 0 else 1.0

        reasoning = [
            f"Entry di zona {entry_min:,.0f}-{entry_max:,.0f} (dekat support {nearest_support:,.0f})",
            f"SL di {sl:,.0f} ({sl_pct:.1f}%) — swing low terdekat",
            f"TP1 di {tp1:,.0f} (+{tp1_pct:.1f}%) — resistance pertama",
        ]

        return TradingPlan(
            symbol=symbol, signal="BUY",
            entry_min=round(entry_min, 0), entry_max=round(entry_max, 0),
            stop_loss=round(sl, 0), sl_pct=round(sl_pct, 1),
            tp1=round(tp1, 0), tp1_pct=round(tp1_pct, 1),
            tp2=round(tp2, 0), tp2_pct=round(tp2_pct, 1),
            rr_ratio=round(rr, 1),
            confidence=0, grade="C",
            reasoning=reasoning,
        )

    # ── Short Plan (SELL) ────────────────────────────────────

    def _generate_short_plan(
        self, symbol: str, price: float, atr: float,
        support: List[float], resistance: List[float],
        closes: np.ndarray, volumes: np.ndarray
    ) -> TradingPlan:
        """Generate SELL trading plan."""
        buffer = price * self.ENTRY_BUFFER_PCT

        # Entry zone
        entry_min = price - buffer
        entry_max = price + buffer

        # Stop Loss: nearest resistance (capped at 8%)
        if resistance:
            candidates = [r for r in resistance if price * 1.02 < r < price * 1.08]
            nearest_resistance = min(candidates) if candidates else price + (atr * self.ATR_SL_MULTIPLIER)
        else:
            nearest_resistance = price + (atr * self.ATR_SL_MULTIPLIER)

        sl = min(nearest_resistance, price * 1.08)  # hard cap 8%
        sl_pct = (sl - price) / price * 100

        # TP1: nearest support
        if support:
            candidates = [s for s in support if s < price * 0.98]
            tp1 = max(candidates) if candidates else price - (atr * self.ATR_TP1_MULTIPLIER)
        else:
            tp1 = price - (atr * self.ATR_TP1_MULTIPLIER)

        tp1_pct = (price - tp1) / price * 100

        # TP2
        if support:
            candidates = [s for s in support if s < tp1 * 0.99]
            tp2 = max(candidates) if candidates else price - (atr * self.ATR_TP2_MULTIPLIER)
        else:
            tp2 = price - (atr * self.ATR_TP2_MULTIPLIER)

        tp2_pct = (price - tp2) / price * 100

        risk = sl - price if sl > price else 0.01
        reward = price - tp1
        rr = reward / risk if risk > 0 else 1.0

        reasoning = [
            f"Entry di zona {entry_min:,.0f}-{entry_max:,.0f} (dekat resistance {nearest_resistance:,.0f})",
            f"SL di {sl:,.0f} (+{sl_pct:.1f}%) — swing high terdekat",
            f"TP1 di {tp1:,.0f} (+{tp1_pct:.1f}%) — support pertama",
        ]

        return TradingPlan(
            symbol=symbol, signal="SELL",
            entry_min=round(entry_min, 0), entry_max=round(entry_max, 0),
            stop_loss=round(sl, 0), sl_pct=round(sl_pct, 1),
            tp1=round(tp1, 0), tp1_pct=round(tp1_pct, 1),
            tp2=round(tp2, 0), tp2_pct=round(tp2_pct, 1),
            rr_ratio=round(rr, 1),
            confidence=0, grade="C",
            reasoning=reasoning,
        )

    # ── Hold Plan ────────────────────────────────────────────

    def _generate_hold_plan(
        self, symbol: str, price: float, atr: float,
        support: List[float], resistance: List[float]
    ) -> TradingPlan:
        """Generate HOLD trading plan — watch zones."""
        sl = support[0] if support else price * 0.95
        tp1 = resistance[-1] if resistance else price * 1.05

        return TradingPlan(
            symbol=symbol, signal="HOLD",
            entry_min=round(price * 0.99, 0), entry_max=round(price * 1.01, 0),
            stop_loss=round(sl, 0), sl_pct=round(abs(price - sl) / price * 100, 1),
            tp1=round(tp1, 0), tp1_pct=round(abs(tp1 - price) / price * 100, 1),
            tp2=round(price * 1.08, 0), tp2_pct=8.0,
            rr_ratio=1.0,
            confidence=0, grade="D",
            reasoning=["Struktur netral — tunggu konfirmasi BOS/CHoCH"],
        )

    # ── Confidence Score (0-20) ──────────────────────────────

    def _calculate_confidence(
        self, signal: str, smc_trend: str,
        accumulation_score: int, volume_ratio: float,
        rr_ratio: float, closes: np.ndarray
    ) -> int:
        """Calculate composite confidence score 0-20.

        Components:
          - Trend alignment (0-5): BULLISH+BUY or BEARISH+SELL = 5, mismatched = 0
          - SMC structure (0-5): clear BOS/CHoCH = 5
          - Accumulation (0-4): bandarmology score / 25
          - Volume confirmation (0-3): volume ratio scoring
          - RR quality (0-3): RR > 2 = 3, RR > 1.5 = 2, RR > 1 = 1
        """
        score = 0

        # 1. Trend alignment (0-5)
        if signal == "BUY" and smc_trend == "BULLISH":
            score += 5
        elif signal == "SELL" and smc_trend == "BEARISH":
            score += 5
        elif signal == "BUY" and smc_trend == "NEUTRAL":
            score += 3
        elif signal == "SELL" and smc_trend == "NEUTRAL":
            score += 3
        elif signal == "HOLD":
            score += 2

        # 2. Accumulation (0-4)
        score += min(4, accumulation_score // 25)

        # 3. Volume confirmation (0-3)
        if volume_ratio > 2.0:
            score += 3
        elif volume_ratio > 1.3:
            score += 2
        elif volume_ratio > 0.8:
            score += 1

        # 4. RR quality (0-3)
        if rr_ratio >= 2.5:
            score += 3
        elif rr_ratio >= 1.5:
            score += 2
        elif rr_ratio >= 1.0:
            score += 1

        # 5. Price momentum (0-5) — position vs moving averages
        if len(closes) >= 20:
            ma20 = np.mean(closes[-20:])
            ma50 = np.mean(closes[-50:]) if len(closes) >= 50 else ma20
            price = closes[-1]

            if signal == "BUY":
                if price > ma20 and ma20 > ma50:
                    score += 5  # Golden alignment
                elif price > ma20:
                    score += 3
                elif price > ma50:
                    score += 1
            elif signal == "SELL":
                if price < ma20 and ma20 < ma50:
                    score += 5
                elif price < ma20:
                    score += 3
                elif price < ma50:
                    score += 1
            else:
                score += 2

        return min(20, score)

    # ── Grade ────────────────────────────────────────────────

    def _assign_grade(self, confidence: int, rr_ratio: float) -> str:
        """Assign A/B/C/D grade based on confidence + RR."""
        if confidence >= 16 and rr_ratio >= 2.0:
            return "A"
        elif confidence >= 12 and rr_ratio >= 1.5:
            return "B"
        elif confidence >= 8:
            return "C"
        else:
            return "D"

    # ── VWAP ─────────────────────────────────────────────────

    def _calculate_vwap(self, ohlc: List[Dict]) -> float:
        """Calculate Volume Weighted Average Price."""
        if not ohlc:
            return 0.0

        total_pv = 0.0
        total_v = 0.0
        for bar in ohlc:
            typical = (bar["high"] + bar["low"] + bar["close"]) / 3
            vol = float(bar.get("volume", 0) or 0)
            total_pv += typical * vol
            total_v += vol

        return total_pv / total_v if total_v > 0 else 0.0


# ── Singleton ───────────────────────────────────────────────────

_engine: Optional[TradingPlanEngine] = None


def get_plan_engine() -> TradingPlanEngine:
    global _engine
    if _engine is None:
        _engine = TradingPlanEngine()
    return _engine
