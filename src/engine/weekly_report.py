"""Auto-Report Mingguan — Premium feature.

Generates weekly market recap every Monday morning (07:00 WIB).
Includes: foreign flow, bandarmology, sentiment, top sectors.

Fully automated — no mentor needed. Just data.
"""

from datetime import datetime, timedelta
from typing import Optional


class WeeklyReportEngine:
    """Generate automated weekly market recap reports.

    Uses RapidAPI broker flow + sentiment + sectors data.
    Designed to be called by cron job every Monday 07:00 WIB.
    """

    WEEKDAYS_ID = {
        0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
        4: "Jumat", 5: "Sabtu", 6: "Minggu",
    }

    def __init__(self):
        self._broker_flow: Optional[dict] = None
        self._sectors: list = []

    async def fetch_data(self):
        """Fetch all needed data from RapidAPI."""
        from src.feed.rapidapi_idx import RapidAPIFeed

        feed = RapidAPIFeed()
        self._broker_flow = await feed.get_broker_flow_summary()
        self._sectors = await feed.get_sectors()
        await feed.close()

    def generate(self) -> str:
        """Generate the full weekly report as formatted text."""
        now = datetime.now()
        weekday = self.WEEKDAYS_ID.get(now.weekday(), "Senin")
        date_str = now.strftime("%d %B %Y")

        out = f"📊 *Laporan Mingguan — {weekday}, {date_str}*\n"
        out += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # ── 1. Market Overview ──
        out += self._section_overview()

        # ── 2. Foreign Flow ──
        out += self._section_foreign_flow()

        # ── 3. Market Sentiment ──
        out += self._section_sentiment()

        # ── 4. Sectors ──
        out += self._section_sectors()

        # ── 5. Tips ──
        out += self._section_tips()

        # ── Footer ──
        out += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        out += f"🤖 Auto-generated oleh IDX AI Bot\n"
        out += f"💎 Upgrade ke Premium: /pricing\n"

        return out

    def _section_overview(self) -> str:
        bf = self._broker_flow or {}
        total = bf.get("total_value", 0)
        out = "🏛 *1. Market Overview*\n"
        out += f"   Total Value: Rp{total:,.0f}\n"
        out += f"   Sektor: {len(self._sectors)} sektor terpantau\n\n"
        return out

    def _section_foreign_flow(self) -> str:
        bf = self._broker_flow or {}
        fnb = bf.get("foreign_net_buy", 0)
        fbr = bf.get("foreign_domestic_ratio", 0) * 100
        fb = bf.get("foreign_buy", 0)
        fs = bf.get("foreign_sell", 0)

        out = "🏦 *2. Foreign Flow*\n"
        if fnb > 200_000_000_000:
            out += f"   🟢 Asing Net Buy: Rp{fnb:,.0f}\n"
        elif fnb < -200_000_000_000:
            out += f"   🔴 Asing Net Sell: Rp{abs(fnb):,.0f}\n"
        else:
            out += f"   ⚪ Asing Net: Rp{fnb:,.0f}\n"
        out += f"   Foreign Ratio: {fbr:.1f}%\n"
        out += f"   Buy: Rp{fb:,.0f} | Sell: Rp{fs:,.0f}\n"

        # Top foreign brokers
        top_brokers = bf.get("top_brokers", [])
        foreign_brokers = [
            b for b in top_brokers
            if b.get("group") == "BROKER_GROUP_FOREIGN"
        ]
        if foreign_brokers:
            out += f"\n   *Top Broker Asing:*\n"
            for b in foreign_brokers[:3]:
                net = float(b.get("net_value", 0) or 0)
                direction = "🔺" if net > 0 else "🔻"
                out += f"   {direction} {b['code']} {b['name']}: Rp{abs(net):,.0f}\n"

        out += "\n"
        return out

    def _section_sentiment(self) -> str:
        from src.engine.market_sentiment import MarketSentimentEngine

        engine = MarketSentimentEngine()
        bf = self._broker_flow or {}
        sentiment = engine.analyze(bf, self._sectors)

        out = "📈 *3. Market Sentiment*\n"
        out += f"   {sentiment.sentiment} — Score: {sentiment.overall_score}/100\n"
        out += f"   {sentiment.summary.split(chr(10))[0]}\n\n"
        return out

    def _section_sectors(self) -> str:
        out = "🏢 *4. Sektor*\n"
        if self._sectors:
            for s in self._sectors[:6]:
                out += f"   • {s.get('name', '?')}\n"
            if len(self._sectors) > 6:
                out += f"   ... dan {len(self._sectors)-6} sektor lainnya\n"
        out += "\n"
        return out

    def _section_tips(self) -> str:
        out = "💡 *5. Tips Minggu Ini*\n"
        bf = self._broker_flow or {}
        fnb = bf.get("foreign_net_buy", 0)

        if fnb > 300_000_000_000:
            out += "   Asing agresif masuk — saatnya entry saham blue chip.\n"
            out += "   Fokus: BBCA, BBRI, TLKM, ASII.\n"
        elif fnb < -300_000_000_000:
            out += "   ⚠️ Asing keluar besar — wait and see.\n"
            out += "   Jangan FOMO. Cash is position.\n"
        else:
            out += "   Pasar sideways — scalping atau wait confirmation.\n"
            out += "   Pantau /bandarmology untuk sinyal akumulasi.\n"
        out += "\n"
        return out


# ── Convenience function ─────────────────────────────────────────

async def generate_weekly_report() -> str:
    """One-shot: fetch data + generate report."""
    engine = WeeklyReportEngine()
    await engine.fetch_data()
    return engine.generate()


# ── Daily Digest (Watchlist companion) ──────────────────────────

async def generate_daily_digest() -> str:
    """Generate daily market snapshot (for watchlist users)."""
    from src.feed.rapidapi_idx import RapidAPIFeed
    from src.engine.market_sentiment import MarketSentimentEngine

    feed = RapidAPIFeed()
    broker = await feed.get_broker_flow_summary()
    sectors = await feed.get_sectors()
    await feed.close()

    now = datetime.now()
    date_str = now.strftime("%d %B %Y, %H:%M WIB")

    sent = MarketSentimentEngine()
    sentiment = sent.analyze(broker, sectors)

    fnb = broker.get("foreign_net_buy", 0)
    fbr = broker.get("foreign_domestic_ratio", 0) * 100

    out = f"📊 *Daily Digest — {date_str}*\n"
    out += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    out += f"{sentiment.sentiment} — Score: {sentiment.overall_score}/100\n\n"
    out += f"🏦 Foreign: {'Net Buy' if fnb>0 else 'Net Sell'} Rp{abs(fnb):,.0f} ({fbr:.1f}%)\n\n"
    out += f"💡 Ketik `analisa BBCA` atau `/bandarmology`\n"
    out += f"━━━━━━━━━━━━━━━━━━━━\n"
    out += f"🤖 IDX AI Bot"

    return out
