"""SMC Structure Engine — BOS/CHoCH Detection + Bandarmology Combo.

Smart Money Concepts structural analysis:
  - BOS (Break of Structure): price breaks previous high → bullish continuation
  - CHoCH (Change of Character): price breaks previous low → bearish reversal
  - Liquidity sweep detection: false break + quick reversal
  - Bandarmology combo: validate structure with volume/accumulation

Tier: PRO+ (structure only) / PREMIUM (combo with bandarmology).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np


# ── Data Classes ─────────────────────────────────────────────────

@dataclass
class SwingPoint:
    """A detected swing high or low."""
    index: int           # position in price array
    price: float
    timestamp: Optional[str] = None
    type: str = ""       # "HIGH" or "LOW"
    volume: float = 0.0


@dataclass
class StructureBreak:
    """A detected BOS or CHoCH event."""
    type: str            # "BOS" (bullish) or "CHoCH" (bearish)
    broken_swing: SwingPoint
    break_price: float
    break_index: int
    previous_trend: str  # "UPTREND" / "DOWNTREND" / "RANGING"
    new_trend: str
    strength: str        # "Strong" / "Moderate" / "Weak"
    false_break: bool = False


@dataclass
class LiquiditySweep:
    """A detected liquidity sweep (fake breakout)."""
    direction: str       # "BULL_TRAP" or "BEAR_TRAP"
    swept_level: float
    sweep_index: int
    reversal_index: int
    reversal_pct: float  # how far it reversed


@dataclass
class SMCReport:
    """Full SMC structure analysis report."""
    symbol: str
    timestamp: str
    trend: str           # "BULLISH" / "BEARISH" / "NEUTRAL"
    swing_highs: List[SwingPoint] = field(default_factory=list)
    swing_lows: List[SwingPoint] = field(default_factory=list)
    recent_bos: List[StructureBreak] = field(default_factory=list)
    recent_choch: List[StructureBreak] = field(default_factory=list)
    liquidity_sweeps: List[LiquiditySweep] = field(default_factory=list)
    key_levels: Dict[str, List[float]] = field(default_factory=dict)
    bandarmology_confirmation: bool = False
    combo_signal: str = ""  # "STRONG_BUY" / "BUY" / "SELL" / "STRONG_SELL" / "NO_SIGNAL"
    combo_confidence: int = 0  # 0-100
    summary: str = ""


# ── Core Engine ──────────────────────────────────────────────────

class SMCStructureEngine:
    """Detect SMC structures: BOS, CHoCH, liquidity sweeps, key levels."""

    SWING_WINDOW = 5        # bars left/right for swing detection
    MIN_SWING_STRENGTH = 0.005  # 0.5% minimum swing size
    SWEEP_REVERSAL_PCT = 0.003  # 0.3% reversal threshold for sweep
    LOOKBACK = 60            # bars to analyze

    def analyze(self, ohlc_data: List[Dict], symbol: str = "") -> SMCReport:
        """Run full SMC analysis on OHLC data."""
        closes = np.array([c["close"] for c in ohlc_data[-self.LOOKBACK:]])
        highs = np.array([c["high"] for c in ohlc_data[-self.LOOKBACK:]])
        lows = np.array([c["low"] for c in ohlc_data[-self.LOOKBACK:]])
        volumes = np.array([c.get("volume", 0) or 0 for c in ohlc_data[-self.LOOKBACK:]])
        timestamps = [c.get("timestamp", "") for c in ohlc_data[-self.LOOKBACK:]]

        if len(closes) < 20:
            return SMCReport(symbol=symbol, timestamp=datetime.now().isoformat(),
                           trend="NEUTRAL", summary="⚠️ Data tidak cukup (butuh min 20 candle).")

        # 1. Detect swing highs and lows
        swing_highs = self._detect_swing_points(highs, "HIGH", volumes, timestamps)
        swing_lows = self._detect_swing_points(lows, "LOW", volumes, timestamps)

        # 2. Detect BOS and CHoCH
        bos_signals, choch_signals = self._detect_structure_breaks(
            highs, lows, closes, swing_highs, swing_lows, volumes, timestamps
        )

        # 3. Detect liquidity sweeps
        sweeps = self._detect_liquidity_sweeps(highs, lows, closes, swing_highs, swing_lows)

        # 4. Determine trend
        trend = self._determine_trend(closes, swing_highs, swing_lows)

        # 5. Extract key levels
        key_levels = self._extract_key_levels(swing_highs, swing_lows, closes)

        # 6. Generate summary
        summary = self._generate_summary(
            trend, bos_signals, choch_signals, sweeps, key_levels
        )

        return SMCReport(
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
            trend=trend,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            recent_bos=bos_signals,
            recent_choch=choch_signals,
            liquidity_sweeps=sweeps,
            key_levels=key_levels,
            summary=summary,
        )

    # ── Swing Detection ──────────────────────────────────────

    def _detect_swing_points(
        self, prices: np.ndarray, ptype: str, volumes: np.ndarray, timestamps: list
    ) -> List[SwingPoint]:
        """Detect swing highs or lows using local maxima/minima."""
        points = []
        w = self.SWING_WINDOW

        for i in range(w, len(prices) - w):
            if ptype == "HIGH":
                is_swing = all(prices[i] >= prices[i - j] for j in range(1, w + 1)) and \
                           all(prices[i] >= prices[i + j] for j in range(1, w + 1))
            else:
                is_swing = all(prices[i] <= prices[i - j] for j in range(1, w + 1)) and \
                           all(prices[i] <= prices[i + j] for j in range(1, w + 1))

            if is_swing:
                # Check minimum swing strength
                if len(points) > 0:
                    prev_price = points[-1].price
                    diff = abs(prices[i] - prev_price) / prev_price
                    if diff < self.MIN_SWING_STRENGTH:
                        continue

                ts = timestamps[i] if i < len(timestamps) else None
                vol = float(volumes[i]) if i < len(volumes) else 0.0
                points.append(SwingPoint(
                    index=i, price=float(prices[i]), timestamp=ts,
                    type=ptype, volume=vol
                ))

        return points[-8:]  # keep last 8 swing points

    # ── Structure Break Detection ────────────────────────────

    def _detect_structure_breaks(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
        swing_highs: List[SwingPoint], swing_lows: List[SwingPoint],
        volumes: np.ndarray, timestamps: list
    ) -> Tuple[List[StructureBreak], List[StructureBreak]]:
        """Detect BOS (bullish) and CHoCH (bearish) events."""
        bos_list = []
        choch_list = []

        # Need at least 2 swing highs and 2 swing lows
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return bos_list, choch_list

        # Current price
        current_close = closes[-1]

        # BOS: price breaks above last significant swing high
        if len(swing_highs) >= 2:
            last_sh = swing_highs[-1]
            prev_sh = swing_highs[-2]

            # Check if we broke the last swing high
            recent_highs = highs[last_sh.index:]
            break_high = any(h > last_sh.price * 1.002 for h in recent_highs)

            if current_close > last_sh.price and break_high:
                # Check for false break (liquidity sweep)
                false_break = self._is_false_break(closes, last_sh.index, "BULL")
                strength = self._break_strength(
                    current_close, last_sh.price, volumes, last_sh.index
                )
                bos_list.append(StructureBreak(
                    type="BOS",
                    broken_swing=last_sh,
                    break_price=current_close,
                    break_index=len(closes) - 1,
                    previous_trend="UPTREND",
                    new_trend="BULLISH_CONTINUATION",
                    strength=strength,
                    false_break=false_break,
                ))

        # CHoCH: price breaks below last significant swing low
        if len(swing_lows) >= 2:
            last_sl = swing_lows[-1]
            prev_sl = swing_lows[-2]

            recent_lows = lows[last_sl.index:]
            break_low = any(lo < last_sl.price * 0.998 for lo in recent_lows)

            if current_close < last_sl.price and break_low:
                false_break = self._is_false_break(closes, last_sl.index, "BEAR")
                strength = self._break_strength(
                    current_close, last_sl.price, volumes, last_sl.index, bearish=True
                )
                choch_list.append(StructureBreak(
                    type="CHoCH",
                    broken_swing=last_sl,
                    break_price=current_close,
                    break_index=len(closes) - 1,
                    previous_trend="DOWNTREND",
                    new_trend="BEARISH_CONTINUATION",
                    strength=strength,
                    false_break=false_break,
                ))

        return bos_list, choch_list

    def _is_false_break(self, closes: np.ndarray, break_idx: int, direction: str) -> bool:
        """Check if a break quickly reversed (liquidity sweep)."""
        if break_idx >= len(closes) - 3:
            return False  # too recent to tell

        post_break = closes[break_idx:]
        if len(post_break) < 3:
            return False

        if direction == "BULL":
            # False bullish break: price goes above then drops back below
            return post_break[-1] < closes[break_idx] * 0.998
        else:
            # False bearish break: price goes below then recovers above
            return post_break[-1] > closes[break_idx] * 1.002

    def _break_strength(
        self, current: float, swing_price: float,
        volumes: np.ndarray, break_idx: int, bearish: bool = False
    ) -> str:
        """Rate break strength based on volume and distance."""
        dist_pct = abs(current - swing_price) / swing_price

        # Volume at break
        vol_recent = volumes[break_idx:] if break_idx < len(volumes) else volumes[-5:]
        vol_avg = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        vol_ratio = np.mean(vol_recent) / vol_avg if vol_avg > 0 else 1.0

        score = 0
        if dist_pct > 0.02: score += 3
        elif dist_pct > 0.01: score += 2
        else: score += 1

        if vol_ratio > 1.5: score += 3
        elif vol_ratio > 1.0: score += 2
        else: score += 0

        if score >= 5: return "Strong"
        elif score >= 3: return "Moderate"
        return "Weak"

    # ── Liquidity Sweeps ─────────────────────────────────────

    def _detect_liquidity_sweeps(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
        swing_highs: List[SwingPoint], swing_lows: List[SwingPoint]
    ) -> List[LiquiditySweep]:
        """Detect liquidity sweeps — fake breakouts that reverse quickly."""
        sweeps = []

        # Bull trap: breaks above swing high then drops sharply
        for sh in swing_highs[-3:]:
            for i in range(sh.index, len(highs)):
                if highs[i] > sh.price * 1.003:
                    # Check if reversed
                    post_sweep = closes[i:]
                    if len(post_sweep) >= 4:
                        reversal = (post_sweep[0] - post_sweep[-1]) / post_sweep[0]
                        if reversal > self.SWEEP_REVERSAL_PCT:
                            sweeps.append(LiquiditySweep(
                                direction="BULL_TRAP",
                                swept_level=sh.price,
                                sweep_index=i,
                                reversal_index=i + len(post_sweep),
                                reversal_pct=round(reversal * 100, 2),
                            ))
                    break

        # Bear trap: dips below swing low then surges up
        for sl in swing_lows[-3:]:
            for i in range(sl.index, len(lows)):
                if lows[i] < sl.price * 0.997:
                    post_sweep = closes[i:]
                    if len(post_sweep) >= 4:
                        reversal = (post_sweep[-1] - post_sweep[0]) / post_sweep[0]
                        if reversal > self.SWEEP_REVERSAL_PCT:
                            sweeps.append(LiquiditySweep(
                                direction="BEAR_TRAP",
                                swept_level=sl.price,
                                sweep_index=i,
                                reversal_index=i + len(post_sweep),
                                reversal_pct=round(reversal * 100, 2),
                            ))
                    break

        return sweeps[-3:]

    # ── Trend ────────────────────────────────────────────────

    def _determine_trend(
        self, closes: np.ndarray,
        swing_highs: List[SwingPoint], swing_lows: List[SwingPoint]
    ) -> str:
        """Determine market structure trend."""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            # Fallback: price vs moving average
            ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)
            if closes[-1] > ma20 * 1.01:
                return "BULLISH"
            elif closes[-1] < ma20 * 0.99:
                return "BEARISH"
            return "NEUTRAL"

        # Higher highs + higher lows = bullish
        hh = swing_highs[-1].price > swing_highs[-2].price
        hl = swing_lows[-1].price > swing_lows[-2].price

        # Lower highs + lower lows = bearish
        lh = swing_highs[-1].price < swing_highs[-2].price
        ll = swing_lows[-1].price < swing_lows[-2].price

        if hh and hl:
            return "BULLISH"
        elif lh and ll:
            return "BEARISH"
        else:
            return "NEUTRAL"

    # ── Key Levels ───────────────────────────────────────────

    def _extract_key_levels(
        self, swing_highs: List[SwingPoint], swing_lows: List[SwingPoint],
        closes: np.ndarray
    ) -> Dict[str, List[float]]:
        """Extract key support & resistance levels from swing points."""
        levels = {
            "resistance": [],
            "support": [],
        }

        # Take latest 3 swing highs as resistance
        for sh in swing_highs[-3:]:
            levels["resistance"].append(round(sh.price, 0))

        # Take latest 3 swing lows as support
        for sl in swing_lows[-3:]:
            levels["support"].append(round(sl.price, 0))

        # Sort descending
        levels["resistance"] = sorted(set(levels["resistance"]), reverse=True)
        levels["support"] = sorted(set(levels["support"]))

        return levels

    # ── Bandarmology Combo ───────────────────────────────────

    def combo_with_bandarmology(
        self, smc_report: SMCReport, accumulation_score: int
    ) -> SMCReport:
        """Validate SMC signals with bandarmology accumulation score."""
        if accumulation_score > 0:
            smc_report.bandarmology_confirmation = True

        # Combo logic
        if smc_report.trend == "BULLISH" and accumulation_score >= 60:
            smc_report.combo_signal = "STRONG_BUY"
            smc_report.combo_confidence = min(100, accumulation_score)
        elif smc_report.trend == "BULLISH" and accumulation_score >= 30:
            smc_report.combo_signal = "BUY"
            smc_report.combo_confidence = accumulation_score
        elif accumulation_score >= 80:
            smc_report.combo_signal = "STRONG_BUY"
            smc_report.combo_confidence = accumulation_score
        elif self._has_bearish_signal(smc_report) and accumulation_score < 20:
            smc_report.combo_signal = "SELL"
            smc_report.combo_confidence = 100 - accumulation_score
        else:
            smc_report.combo_signal = "NO_SIGNAL"
            smc_report.combo_confidence = 0

        return smc_report

    def _has_bearish_signal(self, report: SMCReport) -> bool:
        """Check if report has bearish CHoCH signals."""
        if report.recent_choch:
            return True
        # Also check for bull traps (bearish)
        for sweep in report.liquidity_sweeps:
            if sweep.direction == "BULL_TRAP":
                return True
        return False

    # ── Summary Generator ────────────────────────────────────

    def _generate_summary(
        self, trend: str, bos: List[StructureBreak], choch: List[StructureBreak],
        sweeps: List[LiquiditySweep], key_levels: Dict[str, List[float]]
    ) -> str:
        """Generate human-readable structure summary."""
        lines = []

        # Trend header
        emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}
        lines.append(f"📐 **Market Structure:** {trend} {emoji.get(trend, '')}")

        # BOS signals
        if bos:
            for b in bos[-1:]:  # latest only
                conf = "✅ VALID" if not b.false_break else "⚠️ POTENTIAL FALSE BREAK"
                lines.append(f"🟢 **BOS** {b.strength} | {conf}")
                lines.append(f"   Break high: {b.broken_swing.price:,.0f}")

        # CHoCH signals
        if choch:
            for c in choch[-1:]:
                conf = "✅ VALID" if not c.false_break else "⚠️ POTENTIAL FALSE BREAK"
                lines.append(f"🔴 **CHoCH** {c.strength} | {conf}")
                lines.append(f"   Break low: {c.broken_swing.price:,.0f}")

        # Sweeps
        if sweeps:
            lines.append("")
            lines.append("⚡ **Liquidity Sweeps:**")
            for s in sweeps[-2:]:
                icon = "🐂 BULL TRAP" if s.direction == "BULL_TRAP" else "🐻 BEAR TRAP"
                lines.append(f"   {icon} — reversed {s.reversal_pct}%")

        # Key levels
        if key_levels["resistance"] or key_levels["support"]:
            lines.append("")
            lines.append("📊 **Key Levels:**")
            if key_levels["resistance"]:
                res = ", ".join(f"{r:,.0f}" for r in key_levels["resistance"][:3])
                lines.append(f"   🔴 Resistance: {res}")
            if key_levels["support"]:
                sup = ", ".join(f"{s:,.0f}" for s in key_levels["support"][:3])
                lines.append(f"   🟢 Support: {sup}")

        return "\n".join(lines)


# ── Singleton ───────────────────────────────────────────────────

_smc_engine: Optional[SMCStructureEngine] = None


def get_smc_engine() -> SMCStructureEngine:
    global _smc_engine
    if _smc_engine is None:
        _smc_engine = SMCStructureEngine()
    return _smc_engine
