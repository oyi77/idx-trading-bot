"""Indicator definitions and calculation for IDX stocks."""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class IndicatorResult:
    name: str
    value: float
    signal: str  # bullish / bearish / neutral
    detail: str = ""


# ── Moving Averages ──

def sma(prices: List[float], period: int = 20) -> List[float]:
    """Simple Moving Average."""
    if len(prices) < period:
        return []
    result = []
    for i in range(len(prices) - period + 1):
        result.append(sum(prices[i : i + period]) / period)
    return result


def ema(prices: List[float], period: int = 20, smoothing: float = 2.0) -> List[float]:
    """Exponential Moving Average."""
    if len(prices) < period:
        return []
    k = smoothing / (period + 1)
    result = [sum(prices[:period]) / period]  # first EMA = SMA
    for price in prices[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


# ── RSI ──

def rsi(prices: List[float], period: int = 14) -> float:
    """Relative Strength Index. Returns current RSI value."""
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def rsi_signal(rsi_value: float) -> IndicatorResult:
    if rsi_value >= 70:
        return IndicatorResult("RSI", rsi_value, "bearish", f"Overbought ({rsi_value:.1f})")
    elif rsi_value <= 30:
        return IndicatorResult("RSI", rsi_value, "bullish", f"Oversold ({rsi_value:.1f})")
    return IndicatorResult("RSI", rsi_value, "neutral", f"Normal ({rsi_value:.1f})")


# ── MACD ──

@dataclass
class MACDResult:
    macd: float
    signal: float
    histogram: float
    trend: str  # bullish / bearish


def macd(
    prices: List[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Optional[MACDResult]:
    """Moving Average Convergence Divergence."""
    if len(prices) < slow + signal_period:
        return None
    ema_fast = ema(prices, fast)[-1]
    ema_slow = ema(prices, slow)[-1]
    macd_line = ema_fast - ema_slow

    # Simplified signal line
    macd_values = []
    for i in range(slow, len(prices)):
        ef = ema(prices[: i + 1], fast)[-1]
        es = ema(prices[: i + 1], slow)[-1]
        macd_values.append(ef - es)

    signal_line = sum(macd_values[-signal_period:]) / signal_period if len(macd_values) >= signal_period else macd_line
    histogram = macd_line - signal_line

    return MACDResult(
        macd=macd_line,
        signal=signal_line,
        histogram=histogram,
        trend="bullish" if histogram > 0 else "bearish",
    )


# ── Bollinger Bands ──

@dataclass
class BollingerResult:
    upper: float
    middle: float
    lower: float
    bandwidth: float
    position: str  # above / inside / below


def bollinger(
    prices: List[float], period: int = 20, std_dev: float = 2.0
) -> Optional[BollingerResult]:
    if len(prices) < period:
        return None
    middle = sum(prices[-period:]) / period
    variance = sum((p - middle) ** 2 for p in prices[-period:]) / period
    std = variance ** 0.5
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    current = prices[-1]
    bandwidth = (upper - lower) / middle

    position = "above" if current > upper else ("below" if current < lower else "inside")
    return BollingerResult(upper, middle, lower, bandwidth, position)


# ── SuperTrend ──

@dataclass
class SuperTrendResult:
    trend: str  # bullish / bearish
    line: float
    atr: float


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Average True Range."""
    if len(highs) < period + 1:
        return 0
    trs = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs[-period:]) / period


def supertrend(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 10,
    multiplier: float = 3.0,
) -> SuperTrendResult:
    atr_value = atr(highs, lows, closes, period)
    hl2 = [(h + l) / 2 for h, l in zip(highs, lows)]
    basic_upper = hl2[-1] + multiplier * atr_value
    basic_lower = hl2[-1] - multiplier * atr_value

    # Simple heuristic
    if closes[-1] > basic_upper:
        return SuperTrendResult("bearish", basic_upper, atr_value)
    elif closes[-1] < basic_lower:
        return SuperTrendResult("bullish", basic_lower, atr_value)
    return SuperTrendResult("neutral", hl2[-1], atr_value)


# ── Volume Analysis ──

def volume_spike(volumes: List[int], multiplier: float = 1.5) -> bool:
    """Check if latest volume is above average by multiplier."""
    if len(volumes) < 2:
        return False
    avg = sum(volumes[:-1]) / (len(volumes) - 1)
    return avg > 0 and volumes[-1] >= avg * multiplier


def vwap(highs: List[float], lows: List[float], closes: List[float], volumes: List[int]) -> Optional[float]:
    """Volume Weighted Average Price."""
    if not volumes or not closes:
        return None
    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    total_tp_v = sum(tp * v for tp, v in zip(typical_prices, volumes))
    total_v = sum(volumes)
    return total_tp_v / total_v if total_v > 0 else None


# ── Stochastic Oscillator ──────────────────────────────────────

@dataclass
class StochasticResult:
    k: float
    d: float
    signal: str  # oversold / overbought / neutral


def stochastic(
    highs: List[float], lows: List[float], closes: List[float],
    k_period: int = 14, d_period: int = 3,
) -> Optional[StochasticResult]:
    """Stochastic Oscillator (%K, %D) — momentum indicator 0-100.

    %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %D = 3-period SMA of %K

    Signal: oversold < 20, overbought > 80, neutral otherwise.
    """
    if len(closes) < k_period + d_period:
        return None

    hh = max(highs[-k_period:])
    ll = min(lows[-k_period:])

    if hh == ll:
        return StochasticResult(k=50, d=50, signal="neutral")

    k = (closes[-1] - ll) / (hh - ll) * 100

    # Calculate previous %K values for %D smoothing
    k_values = []
    for i in range(-d_period, 0):
        hh_i = max(highs[i - k_period + 1:i + 1])
        ll_i = min(lows[i - k_period + 1:i + 1])
        if hh_i != ll_i:
            k_values.append((closes[i] - ll_i) / (hh_i - ll_i) * 100)
        else:
            k_values.append(50)

    d = sum(k_values) / len(k_values) if k_values else k

    if k < 20:
        signal = "oversold"
    elif k > 80:
        signal = "overbought"
    else:
        signal = "neutral"

    return StochasticResult(k=round(k, 1), d=round(d, 1), signal=signal)
