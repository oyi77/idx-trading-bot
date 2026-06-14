"""Trending stock analysis — identify stocks with strong momentum.

Uses Yahoo Finance for price data. Zero API cost.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class TrendingStock:
    symbol: str
    name: str = ""
    price: float = 0.0
    change_1w: float = 0.0    # % change in 1 week
    change_1m: float = 0.0    # % change in 1 month
    volume_ratio: float = 1.0  # avg volume(1w) / avg volume(3m)
    momentum_score: int = 0    # 0-10
    direction: str = "neutral"  # up / down / neutral
    rsi: float = 50.0


@dataclass
class TrendingReport:
    top_gainers: list[TrendingStock] = field(default_factory=list)
    top_losers: list[TrendingStock] = field(default_factory=list)
    most_active: list[TrendingStock] = field(default_factory=list)
    generated_at: str = ""
    total_analyzed: int = 0


# Popular IDX stocks to track (top market cap + liquid)
IDX_STOCKS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK",
    "ADRO.JK", "UNVR.JK", "ICBP.JK", "INDF.JK", "PTBA.JK",
    "ANTM.JK", "GGRM.JK", "HMSP.JK", "UNTR.JK", "KLBF.JK",
    "PGAS.JK", "SMGR.JK", "CPIN.JK", "AMRT.JK", "ACES.JK",
    "BRIS.JK", "TOWR.JK", "EXCL.JK", "ISAT.JK", "MTEL.JK",
    "BUKA.JK", "GOTO.JK", "EMTK.JK", "MDKA.JK", "HRUM.JK",
    "BRPT.JK", "INKP.JK", "ITMG.JK", "JSMR.JK", "PWON.JK",
    "TBIG.JK", "TINS.JK", "WIKA.JK", "WSKT.JK",
]


def _compute_rsi(prices: list[float], period: int = 14) -> float:
    """Compute RSI for a price series."""
    if len(prices) < period + 1:
        return 50.0

    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = prices[-(period + 1) + i] - prices[-(period + 1) + i - 1]
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    if not losses:
        return 100.0
    if not gains:
        return 0.0

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


async def analyze_trending(
    symbols: Optional[list[str]] = None,
    max_stocks: int = 40,
) -> TrendingReport:
    """Analyze trending stocks from IDX.

    Args:
        symbols: List of symbols with .JK suffix (defaults to IDX_STOCKS)
        max_stocks: Max number of stocks to analyze

    Returns:
        TrendingReport with top gainers, losers, and most active
    """
    from datetime import datetime

    symbols = symbols or IDX_STOCKS
    symbols = symbols[:max_stocks]

    results: list[TrendingStock] = []
    total = len(symbols)

    for i, sym in enumerate(symbols):
        try:
            ticker = yf.Ticker(sym)
            name = ticker.info.get("shortName", sym.replace(".JK", ""))
            # Fetch 3 months of daily data
            hist = ticker.history(period="3mo")

            if len(hist) < 10:
                continue

            prices = hist["Close"].tolist()
            volumes = hist["Volume"].tolist()

            # Current price
            price = prices[-1] if prices else 0
            if price <= 0:
                continue

            # 1-week change (5 trading days)
            if len(prices) >= 5:
                change_1w = ((prices[-1] - prices[-5]) / prices[-5]) * 100
            else:
                change_1w = 0.0

            # 1-month change (21 trading days)
            if len(prices) >= 21:
                change_1m = ((prices[-1] - prices[-21]) / prices[-21]) * 100
            else:
                change_1m = 0.0

            # Volume ratio: avg last 5 days vs avg last 60 days
            if len(volumes) >= 5:
                vol_5d = sum(volumes[-5:]) / 5
                vol_60d = sum(volumes[-60:]) / min(len(volumes), 60) if len(volumes) >= 60 else vol_5d
                volume_ratio = vol_5d / vol_60d if vol_60d > 0 else 1.0
            else:
                volume_ratio = 1.0

            # RSI
            rsi = _compute_rsi(prices)

            # Direction
            if change_1w > 2:
                direction = "up"
            elif change_1w < -2:
                direction = "down"
            else:
                direction = "neutral"

            # Momentum score (0-10): combine % change, volume, and RSI
            score = 5
            # Price momentum
            if change_1w > 10:
                score += 3
            elif change_1w > 5:
                score += 2
            elif change_1w > 2:
                score += 1
            elif change_1w < -10:
                score -= 3
            elif change_1w < -5:
                score -= 2
            elif change_1w < -2:
                score -= 1
            # Volume bonus
            if volume_ratio > 1.5:
                score += 2
            elif volume_ratio > 1.2:
                score += 1
            # RSI adjustment
            if rsi > 70:
                score -= 1  # Overbought
            elif rsi < 30:
                score += 1  # Oversold potential bounce

            score = max(0, min(10, score))

            results.append(TrendingStock(
                symbol=sym.replace(".JK", ""),
                name=name,
                price=price,
                change_1w=change_1w,
                change_1m=change_1m,
                volume_ratio=volume_ratio,
                momentum_score=score,
                direction=direction,
                rsi=rsi,
            ))
        except Exception as e:
            logger.warning(f"Trending: {sym} failed — {e}")
            continue

    # Sort categories
    gainers = sorted(
        [r for r in results if r.change_1w > 0],
        key=lambda x: x.change_1w, reverse=True,
    )[:10]
    losers = sorted(
        [r for r in results if r.change_1w < 0],
        key=lambda x: x.change_1w,
    )[:10]
    most_active = sorted(
        results, key=lambda x: x.volume_ratio, reverse=True,
    )[:10]

    return TrendingReport(
        top_gainers=gainers,
        top_losers=losers,
        most_active=most_active,
        generated_at=datetime.now().strftime("%d %B %Y, %H:%M WIB"),
        total_analyzed=len(results),
    )


def format_trending(report: TrendingReport) -> str:
    """Format trending report for Telegram display."""
    out = f"🔥 *Trending Saham Minggu Ini*\n"
    out += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    out += f"📅 {report.generated_at}\n"
    out += f"📊 {report.total_analyzed} saham dianalisa\n\n"

    if report.top_gainers:
        out += "🟢 *Top Gainers (1 Minggu):*\n"
        for s in report.top_gainers[:7]:
            vol_flag = " 🔥" if s.volume_ratio > 1.5 else ""
            out += f"  • *{s.symbol}* +{s.change_1w:+.1f}% (Rp{s.price:,.0f}){vol_flag}\n"
        out += "\n"

    if report.top_losers:
        out += "🔴 *Top Losers (1 Minggu):*\n"
        for s in report.top_losers[:7]:
            out += f"  • *{s.symbol}* {s.change_1w:+.1f}% (Rp{s.price:,.0f})\n"
        out += "\n"

    if report.most_active:
        out += "📈 *Volume Tertinggi:*\n"
        for s in report.most_active[:5]:
            out += f"  • *{s.symbol}* — {s.volume_ratio:.1f}x normal\n"
        out += "\n"

    out += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    out += "💡 Analisa detail: `analisa <kode>`\n"
    out += "💎 Premium: `/sector` untuk forecast sektor"

    return out
