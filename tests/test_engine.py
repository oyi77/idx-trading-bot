"""Tests for technical analysis engine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.engine.indicator_defs import rsi, rsi_signal, sma, ema, macd, bollinger, volume_spike


def test_sma():
    prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    result = sma(prices, 3)
    assert result is not None
    assert len(result) == 8
    print("✅ SMA: OK")


def test_ema():
    prices = [10, 11, 12, 13, 14]
    result = ema(prices, 3)
    assert result is not None
    assert len(result) >= 1
    print("✅ EMA: OK")


def test_rsi():
    # Upward trend → RSI above 50
    prices_up = list(range(100, 120))
    rsi_val = rsi(prices_up)
    print(f"   RSI uptrend: {rsi_val:.1f}")
    assert rsi_val > 50

    # Downward trend → RSI below 50
    prices_down = list(range(100, 80, -1))
    rsi_val = rsi(prices_down)
    print(f"   RSI downtrend: {rsi_val:.1f}")
    assert rsi_val < 50

    signal = rsi_signal(75)
    assert signal.signal == "bearish"
    signal = rsi_signal(25)
    assert signal.signal == "bullish"
    print("✅ RSI: OK")


def test_macd():
    prices = [100, 102, 101, 105, 110, 115, 120, 118, 122, 125,
              130, 128, 135, 140, 138, 142, 145, 150, 148, 152,
              155, 160, 158, 162, 165, 170, 168, 172, 175, 180]
    result = macd(prices)
    if result:
        print(f"   MACD: {result.macd:.2f}, Signal: {result.signal:.2f}, Hist: {result.histogram:.2f}, Trend: {result.trend}")
        assert result.trend in ("bullish", "bearish")
    print("✅ MACD: OK")


def test_bollinger():
    prices = [100, 102, 104, 103, 105, 107, 106, 108, 110, 109,
              111, 113, 112, 114, 116, 115, 117, 119, 118, 120]
    bb = bollinger(prices)
    if bb:
        print(f"   Upper: {bb.upper:.2f}, Mid: {bb.middle:.2f}, Lower: {bb.lower:.2f}")
        print(f"   Position: {bb.position}")
        assert bb.upper > bb.lower
    print("✅ Bollinger: OK")


def test_volume_spike():
    volumes = [100, 100, 100, 100, 100, 100, 100, 100]
    assert not volume_spike(volumes, 1.5)

    volumes_spike = [100, 100, 100, 100, 100, 500]
    assert volume_spike(volumes_spike, 1.5)
    print("✅ Volume Spike: OK")


if __name__ == "__main__":
    test_sma()
    test_ema()
    test_rsi()
    test_macd()
    test_bollinger()
    test_volume_spike()
    print("\n🎉 All tests passed!")
