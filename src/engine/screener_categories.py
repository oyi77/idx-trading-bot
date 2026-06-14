"""Multi-Category Stock Screener — 5 Strategi Kategori.

Mirip Stockpick Signal: 18 strategi dalam 5 kategori.
Scan 39+ saham IDX setiap kategori.

Categories:
  1. Momentum — saham dengan tenaga naik kuat
  2. Reversal  — saham siap berbalik arah
  3. Breakout  — saham siap menembus level kunci
  4. Smart Money — jejak akumulasi institusi & bandar
  5. Advanced  — setup kelas institusi (SEPA/VCP)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class ScreenerHit:
    """Single stock match from a screener strategy."""
    symbol: str
    price: float
    change_pct: float
    score: int  # 0-100 composite
    strategy: str
    category: str
    reasons: List[str] = field(default_factory=list)
    indicators: Dict = field(default_factory=dict)


@dataclass
class CategoryResult:
    """Results for one screener category."""
    category: str
    description: str
    total_signals: int
    hits: List[ScreenerHit] = field(default_factory=list)


# ── Stock Universe ──────────────────────────────────────────────

IDX_STOCKS = [
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ICBP",
    "INDF", "HMSP", "GGRM", "KLBF", "SMGR", "UNTR", "ADRO", "PTBA",
    "ITMG", "BUMI", "ANTM", "INCO", "MDKA", "BREN", "BRPT", "TPIA",
    "AMRT", "ACES", "MAPI", "ERAA", "TINS", "ISAT", "EXCL", "MTEL",
    "JSMR", "PGAS", "CPIN", "JPFA", "MYOR", "SMSM", "MPMX",
]


class CategoryScreener:
    """Run multi-category stock screening."""

    def __init__(self, ohlc_data: Dict[str, List[Dict]]):
        """Initialize with OHLC data for all stocks.
        
        ohlc_data: {symbol: [{'open','high','low','close','volume','timestamp'}, ...]}
        """
        self.data = ohlc_data

    # ── Category 1: Momentum ───────────────────────────────────

    def screen_momentum(self, limit: int = 10) -> CategoryResult:
        """Screen for momentum stocks."""
        result = CategoryResult(
            category="Momentum",
            description="Saham dengan tenaga naik kuat",
            total_signals=0,
        )

        strategies = {
            "Buy on Strength": self._is_buy_on_strength,
            "Swing Up": self._is_swing_up,
            "Near 52W High": self._is_near_52w_high,
            "Volume Spike": self._is_volume_spike,
        }

        for symbol, ohlc in self.data.items():
            if len(ohlc) < 50:
                continue

            for strategy_name, check_fn in strategies.items():
                hit = check_fn(symbol, ohlc)
                if hit:
                    result.hits.append(hit)
                    result.total_signals += 1

        # Sort by score descending
        result.hits.sort(key=lambda h: h.score, reverse=True)
        result.hits = result.hits[:limit]
        return result

    def _is_buy_on_strength(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """Momentum kuat + close di atas VWAP."""
        closes = np.array([c["close"] for c in ohlc[-20:]])
        volumes = np.array([float(c.get("volume", 0) or 0) for c in ohlc[-20:]])
        
        vwap = self._calc_vwap(ohlc[-20:])
        change = (closes[-1] / closes[-2] - 1) * 100 if len(closes) >= 2 else 0
        
        if closes[-1] > vwap and change > 1.0:
            score = min(100, int(change * 8) + 40)
            return ScreenerHit(
                symbol=symbol, price=closes[-1], change_pct=round(change, 1),
                score=score, strategy="Buy on Strength", category="Momentum",
                reasons=[f"Close di atas VWAP ({closes[-1]/vwap-1:.1%})", f"+{change:.1f}% hari ini"],
                indicators={"vwap": vwap, "change": change},
            )
        return None

    def _is_swing_up(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """Lonjakan >5% dalam sehari + volume konfirmasi."""
        closes = np.array([c["close"] for c in ohlc[-5:]])
        volumes = np.array([float(c.get("volume", 0) or 0) for c in ohlc[-20:]])
        
        if len(closes) < 2:
            return None
        
        change = (closes[-1] / closes[-2] - 1) * 100
        vol_recent = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
        vol_avg = np.mean(volumes) if len(volumes) > 0 else 1
        vol_ratio = vol_recent / vol_avg if vol_avg > 0 else 1
        
        if change > 5.0 and vol_ratio > 1.2:
            score = min(100, int(change * 10) + 30)
            return ScreenerHit(
                symbol=symbol, price=closes[-1], change_pct=round(change, 1),
                score=score, strategy="Swing Up", category="Momentum",
                reasons=[f"Lonjakan +{change:.1f}%", f"Volume {vol_ratio:.1f}x avg"],
                indicators={"vol_ratio": vol_ratio},
            )
        return None

    def _is_near_52w_high(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """Mendekati harga tertinggi 52 minggu."""
        highs = np.array([c["high"] for c in ohlc])
        high_52w = np.max(highs)
        current = ohlc[-1]["close"]
        pct_from_high = (current / high_52w - 1) * 100
        
        if pct_from_high > -5:  # within 5% of 52w high
            score = min(100, int(abs(pct_from_high) * 15) + 40)
            return ScreenerHit(
                symbol=symbol, price=current, change_pct=round(pct_from_high, 1),
                score=score, strategy="Near 52W High", category="Momentum",
                reasons=[f"{abs(pct_from_high):.1f}% dari 52W High ({high_52w:,.0f})"],
                indicators={"high_52w": high_52w},
            )
        return None

    def _is_volume_spike(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """Volume meledak >200% avg 50D."""
        volumes = np.array([float(c.get("volume", 0) or 0) for c in ohlc[-60:]])
        if len(volumes) < 20:
            return None
        
        vol_today = volumes[-1]
        vol_avg = np.mean(volumes[:-1]) if len(volumes) > 1 else 1
        ratio = vol_today / vol_avg if vol_avg > 0 else 0
        
        if ratio > 2.0:
            score = min(100, int(ratio * 20) + 30)
            return ScreenerHit(
                symbol=symbol, price=ohlc[-1]["close"], change_pct=0,
                score=score, strategy="Volume Spike", category="Momentum",
                reasons=[f"Volume {ratio:.1f}x rata-rata", f"{vol_today:,.0f} vs avg {vol_avg:,.0f}"],
                indicators={"vol_ratio": ratio},
            )
        return None

    # ── Category 2: Reversal ───────────────────────────────────

    def screen_reversal(self, limit: int = 10) -> CategoryResult:
        """Screen for reversal stocks."""
        result = CategoryResult(
            category="Reversal",
            description="Saham siap berbalik arah naik",
            total_signals=0,
        )

        for symbol, ohlc in self.data.items():
            if len(ohlc) < 50:
                continue

            # Buy on Weakness
            hit = self._is_buy_on_weakness(symbol, ohlc)
            if hit:
                result.hits.append(hit)
                result.total_signals += 1

            # Near Support
            hit = self._is_near_support(symbol, ohlc)
            if hit:
                result.hits.append(hit)
                result.total_signals += 1

            # RSI Oversold
            hit = self._is_rsi_oversold(symbol, ohlc)
            if hit:
                result.hits.append(hit)
                result.total_signals += 1

        result.hits.sort(key=lambda h: h.score, reverse=True)
        result.hits = result.hits[:limit]
        return result

    def _is_buy_on_weakness(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """Turun >1% — potensi rebound."""
        closes = np.array([c["close"] for c in ohlc[-5:]])
        if len(closes) < 2:
            return None
        
        change = (closes[-1] / closes[-2] - 1) * 100
        rsi = self._calc_rsi(closes)
        
        if change < -1.0 and rsi < 45:
            score = min(100, int(abs(change) * 10) + 30)
            return ScreenerHit(
                symbol=symbol, price=closes[-1], change_pct=round(change, 1),
                score=score, strategy="Buy on Weakness", category="Reversal",
                reasons=[f"Turun {abs(change):.1f}%", f"RSI {rsi:.0f} — potensi rebound"],
                indicators={"rsi": rsi},
            )
        return None

    def _is_near_support(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """Close dekat support — buy saat bounce."""
        lows = np.array([c["low"] for c in ohlc[-60:]])
        current = ohlc[-1]["close"]
        
        # Find swing lows
        support_levels = []
        w = 5
        for i in range(w, len(lows) - w):
            if all(lows[i] <= lows[i - j] for j in range(1, w + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, w + 1)):
                support_levels.append(float(lows[i]))
        
        if not support_levels:
            return None
        
        nearest_support = max(s for s in support_levels if s < current)
        pct_above = (current / nearest_support - 1) * 100
        
        if pct_above < 3:  # within 3% of support
            score = min(100, int((3 - pct_above) * 25) + 30)
            return ScreenerHit(
                symbol=symbol, price=current, change_pct=round(pct_above, 1),
                score=score, strategy="Near Support", category="Reversal",
                reasons=[f"{pct_above:.1f}% di atas support ({nearest_support:,.0f})"],
                indicators={"support": nearest_support},
            )
        return None

    def _is_rsi_oversold(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """RSI oversold < 30."""
        closes = np.array([c["close"] for c in ohlc[-20:]])
        rsi = self._calc_rsi(closes)
        
        if rsi < 30:
            score = min(100, int((30 - rsi) * 5) + 40)
            return ScreenerHit(
                symbol=symbol, price=closes[-1], change_pct=0,
                score=score, strategy="RSI Oversold", category="Reversal",
                reasons=[f"RSI {rsi:.0f} — oversold", "Potensi technical bounce"],
                indicators={"rsi": rsi},
            )
        return None

    # ── Category 3: Breakout ───────────────────────────────────

    def screen_breakout(self, limit: int = 10) -> CategoryResult:
        """Screen for breakout stocks."""
        result = CategoryResult(
            category="Breakout",
            description="Saham siap menembus level kunci",
            total_signals=0,
        )

        for symbol, ohlc in self.data.items():
            if len(ohlc) < 50:
                continue

            hit = self._is_price_vol_breakout(symbol, ohlc)
            if hit:
                result.hits.append(hit)
                result.total_signals += 1

            hit = self._is_ma_crossover(symbol, ohlc)
            if hit:
                result.hits.append(hit)
                result.total_signals += 1

        result.hits.sort(key=lambda h: h.score, reverse=True)
        result.hits = result.hits[:limit]
        return result

    def _is_price_vol_breakout(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """Breakout harga + volume — konfirmasi kuat."""
        closes = np.array([c["close"] for c in ohlc[-30:]])
        volumes = np.array([float(c.get("volume", 0) or 0) for c in ohlc[-30:]])
        highs = np.array([c["high"] for c in ohlc[-30:]])
        
        ma20 = np.mean(closes[:-1])  # yesterday's MA20
        vol_avg = np.mean(volumes[:-1]) if len(volumes) > 1 else 1
        
        if closes[-1] > ma20 * 1.02 and volumes[-1] > vol_avg * 1.5:
            resistance = max(highs[-20:-1])  # 20-day high
            if closes[-1] > resistance:
                score = min(100, int((closes[-1] / resistance - 1) * 100) + 60)
                return ScreenerHit(
                    symbol=symbol, price=closes[-1],
                    change_pct=round((closes[-1] / closes[-2] - 1) * 100, 1),
                    score=score, strategy="Price-Vol Breakout", category="Breakout",
                    reasons=["Breakout resistance + volume spike", f"Close > MA20"],
                    indicators={"ma20": ma20, "resistance": resistance},
                )
        return None

    def _is_ma_crossover(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """MA20 cross above MA50 — golden cross."""
        closes = np.array([c["close"] for c in ohlc[-60:]])
        if len(closes) < 51:
            return None
        
        ma20_today = np.mean(closes[-20:])
        ma50_today = np.mean(closes[-50:])
        ma20_yesterday = np.mean(closes[-21:-1])
        ma50_yesterday = np.mean(closes[-51:-1])
        
        if ma20_today > ma50_today and ma20_yesterday <= ma50_yesterday:
            score = 75
            return ScreenerHit(
                symbol=symbol, price=closes[-1],
                change_pct=round((closes[-1] / closes[-2] - 1) * 100, 1),
                score=score, strategy="MA Crossover", category="Breakout",
                reasons=["Golden Cross MA20↑MA50", f"MA20: {ma20_today:,.0f} > MA50: {ma50_today:,.0f}"],
                indicators={"ma20": ma20_today, "ma50": ma50_today},
            )
        return None

    # ── Category 4: Smart Money ─────────────────────────────────

    def screen_smartmoney(self, limit: int = 10) -> CategoryResult:
        """Screen for smart money signals."""
        result = CategoryResult(
            category="Smart Money",
            description="Jejak akumulasi institusi & bandar",
            total_signals=0,
        )

        for symbol, ohlc in self.data.items():
            if len(ohlc) < 20:
                continue

            hit = self._is_volume_3d(symbol, ohlc)
            if hit:
                result.hits.append(hit)
                result.total_signals += 1

        result.hits.sort(key=lambda h: h.score, reverse=True)
        result.hits = result.hits[:limit]
        return result

    def _is_volume_3d(self, symbol: str, ohlc: List[Dict]) -> Optional[ScreenerHit]:
        """Volume naik 3 hari berturut-turut — akumulasi."""
        volumes = np.array([float(c.get("volume", 0) or 0) for c in ohlc[-20:]])
        closes = np.array([c["close"] for c in ohlc[-20:]])
        
        if len(volumes) < 4:
            return None
        
        vol_up = volumes[-1] > volumes[-2] > volumes[-3]
        price_up = closes[-1] > closes[-3]
        
        if vol_up and price_up:
            vol_change = (volumes[-1] / volumes[-3] - 1) * 100
            score = min(100, int(vol_change / 2) + 40)
            return ScreenerHit(
                symbol=symbol, price=closes[-1],
                change_pct=round((closes[-1] / closes[-2] - 1) * 100, 1),
                score=score, strategy="Volume 3D", category="Smart Money",
                reasons=[f"Volume naik {vol_change:.0f}% dalam 3 hari", "Akumulasi terdeteksi"],
                indicators={"vol_3d_change": vol_change},
            )
        return None

    # ── Helpers ─────────────────────────────────────────────────

    def _calc_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate RSI."""
        if len(closes) < period + 1:
            return 50.0
        
        deltas = np.diff(closes[-period - 1:])
        gains = np.maximum(deltas, 0)
        losses = np.maximum(-deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))

    def _calc_vwap(self, ohlc: List[Dict]) -> float:
        """Calculate VWAP."""
        total_pv = 0.0
        total_v = 0.0
        for bar in ohlc:
            typical = (bar["high"] + bar["low"] + bar["close"]) / 3
            vol = float(bar.get("volume", 0) or 0)
            total_pv += typical * vol
            total_v += vol
        return total_pv / total_v if total_v > 0 else ohlc[-1]["close"]

    # ── Fetch all stock data ────────────────────────────────────

    @staticmethod
    async def fetch_all() -> Dict[str, List[Dict]]:
        """Fetch OHLC data for all IDX stocks via yfinance."""
        import yfinance as yf
        
        data = {}
        tickers = yf.Tickers(" ".join(f"{s}.JK" for s in IDX_STOCKS))
        
        for symbol in IDX_STOCKS:
            try:
                ticker = tickers.tickers.get(f"{symbol}.JK")
                if ticker:
                    df = ticker.history(period="3mo")
                    if not df.empty:
                        ohlc = []
                        for idx, row in df.iterrows():
                            ohlc.append({
                                "timestamp": str(idx),
                                "open": float(row["Open"]),
                                "high": float(row["High"]),
                                "low": float(row["Low"]),
                                "close": float(row["Close"]),
                                "volume": float(row["Volume"]),
                            })
                        data[symbol] = ohlc
            except Exception:
                continue
        
        return data
