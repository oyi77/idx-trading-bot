"""
Daily AI Briefing Engine — morning market snapshot for IDX traders.
Compiles IHSG, sectors, top movers, event news into a rich briefing card.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

LOG = logging.getLogger(__name__)


async def get_top_movers(n: int = 5) -> list[dict]:
    """Get top N IDX stocks by absolute change (gainers + losers)."""
    import yfinance as yf

    symbols = [
        "BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK",
        "ADRO.JK", "UNVR.JK", "ICBP.JK", "INDF.JK", "PTBA.JK",
        "ANTM.JK", "GGRM.JK", "HMSP.JK", "UNTR.JK", "KLBF.JK",
        "PGAS.JK", "SMGR.JK", "CPIN.JK", "AMRT.JK", "ACES.JK",
        "BRIS.JK", "TOWR.JK", "EXCL.JK", "ISAT.JK", "MTEL.JK",
        "BUKA.JK", "GOTO.JK", "MDKA.JK", "HRUM.JK", "MEDC.JK",
    ]

    results = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2d")
            if len(hist) < 2:
                continue
            prev_close = hist["Close"].iloc[-2]
            latest = hist["Close"].iloc[-1]
            change_pct = (latest - prev_close) / prev_close * 100
            results.append({
                "symbol": sym.replace(".JK", ""),
                "price": latest,
                "change_pct": round(change_pct, 2),
            })
        except Exception:
            continue

    results.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return results[:n]


async def build_briefing() -> str:
    """Build full morning briefing card."""
    from src.feed.ihsg_data import get_ihsg_summary

    ihsg = get_ihsg_summary()
    today = date.today().strftime("%d %b %Y")

    # Get top movers
    movers = await get_top_movers(5)

    # IHSG trend emoji
    if ihsg["ytd_return"] > 5:
        ihsg_emoji = "🟢"
        ihsg_label = "Bullish"
    elif ihsg["ytd_return"] > -5:
        ihsg_emoji = "🟡"
        ihsg_label = "Sideways"
    else:
        ihsg_emoji = "🔴"
        ihsg_label = "Bearish"

    # Build card
    card = (
        f"☀️ *Daily AI Briefing*\n"
        f"📅 {today}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    # IHSG
    card += (
        f"📊 *IHSG*\n"
        f"   Harga: *{ihsg['latest_price']:,.0f}*\n"
        f"   {ihsg_emoji} YTD: {ihsg['ytd_return']:+.1f}% ({ihsg_label})\n"
        f"   📈 ATH: {ihsg['ath']:,.0f} ({ihsg['pct_from_ath']:+.1f}%)\n"
        f"   📊 Volatilitas 30d: {ihsg['volatility_30d']:.1f}%\n\n"
    )

    # Top Movers
    if movers:
        card += "🔥 *Top Movers Hari Ini*\n"
        for m in movers:
            emoji = "🟢" if m["change_pct"] > 0 else "🔴"
            card += (
                f"   {emoji} *{m['symbol']}* — {m['price']:,.0f} "
                f"({m['change_pct']:+.1f}%)\n"
            )
        card += "\n"

    # Quick tips
    tips = [
        "💡 `analisa BBCA` — full technical + fundamental + bandar",
        "🔍 `screener akumulasi asing` — saham diakumulasi asing",
        "📊 `screener fundamental bagus` — saham murah berkualitas",
        "🎰 `/bandarmology BBCA` — deteksi bandar real-time (Premium)",
        "📈 `/sector` — forecast volatilitas 11 sektor (Premium)",
        "📰 `/event BBCA` — klasifikasi berita korporat (Premium)",
    ]
    import random
    random.shuffle(tips)
    card += "💡 *Quick Actions*\n" + "\n".join(tips[:3]) + "\n\n"

    card += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *Premium:* `/upgrade` untuk akses penuh"
    )

    return card


if __name__ == "__main__":
    async def main():
        card = await build_briefing()
        print(card)

    asyncio.run(main())
