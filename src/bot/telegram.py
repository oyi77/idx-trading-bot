"""Telegram bot handlers — entry points for all user interactions."""
from typing import Optional

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

from src.config import settings
from src.feed.manager import FeedManager
from src.nlp.router import Intent, NLPRouter
from src.nlp.prompts import DISCLAIMER

logger = logging.getLogger(__name__)


# States for ConversationHandler
AWAITING_SYMBOL = 1


class BotHandlers:
    """Register all Telegram bot handlers."""

    def __init__(self):
        self.nlp = NLPRouter()
        self.feed = None  # lazy init
        self._db = None

    async def _get_feed(self):
        if self.feed is None:
            from src.feed.manager import FeedManager
            self.feed = FeedManager()
        return self.feed

    async def _get_db(self):
        """Get async DB session."""
        if self._db is None:
            from src.models import get_engine, Base
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.ext.asyncio import AsyncSession
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            self._db = Session()
        return self._db

    # ── Start / Help ──

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🚀 *Vilona Saham — AI Co-Pilot Trading IDX*\n\n"
            "Satu-satunya bot yang kasih **TradingView chart** + **AI insight** + **Bandar flow** "
            "dalam 10 detik.\n\n"
            "📌 *Coba sekarang:*\n"
            "• `analisa TLKM` — analisa lengkap + chart + bandar\n"
            "• `screener akumulasi asing` — screening saham\n"
            "• `backtest BBCA` — validasi performa 3 tahun\n"
            "• `/bandarmology` — deteksi akumulasi bandar asing\n"
            "• `/sector` — forecast volatilitas 11 sektor\n"
            "• `/event <berita>` — klasifikasi event korporat\n"
            "• `/watchlist` — pantau saham favorit\n"
            "• `/ihsg` — ringkasan market 30 tahun\n\n"
            "💡 *3.000+ analisa udah dihasilkan.* Gak perlu hafal 300 command. "
            "Cukup ketik natural.\n\n"
            "━━━━━━━━━━━━━━━━━\n"
            "🎁 *Coba Premium gratis 7 hari* — /pricing\n"
            "📖 *Bantuan* — /help"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "📖 *Bantuan Vilona Saham*\n\n"
            "Cukup ketik natural — gak perlu hafal command:\n\n"
            "*📊 Analisa Saham*\n"
            "• `analisa TLKM` — teknikal + fundamental + bandar flow\n"
            "• `backtest BBCA` — validasi performa 3 tahun\n"
            "• `stats TLKM` — high, low, volume, nilai\n\n"
            "*☀️ Briefing & Pasar*\n"
            "• `/briefing` — ringkasan pasar harian (IHSG + top movers)\n"
            "• `/news` — berita pasar terbaru (umum)\n"
            "• `/news BBCA` — berita spesifik saham\n"
            "• `/report` — laporan mingguan lengkap (foreign flow + sektor + sentiment)\n"
            "• `/trending` — saham trending minggu ini (top gainers/losers)🔥\n"
            "• `/ihsg` — ringkasan IHSG (data real-time)\n"
            "• `/sector` — forecast volatilitas 11 sektor (7 hari)\n\n"
            "*🎰 Bandar & Sentiment*\n"
            "• `/bandarmology` — deteksi akumulasi bandar asing\n"
            "• `/event <berita>` — klasifikasi event korporat (11 kelas)\n"
            "• `/watchlist` — pantau saham favorit (daily digest)\n"
            "• `/watchlist add BBCA` — tambah ke watchlist\n\n"
            "*🔍 Screening*\n"
            "• `screener akumulasi asing` — saham diakumulasi asing\n"
            "• `screener volume spike` — saham dengan volume tinggi\n\n"
            "*📋 Trading Plan*\n"
            "• `plan TLKM entry 4600 sl 4500 tp 4800`\n\n"
            "*🔔 Alert Harga*\n"
            "• `alert TLKM >4600` — notifikasi harga menyentuh level\n\n"
            "*💳 Akun*\n"
            "• /pricing — lihat paket langganan\n"
            "• /myplans — trading plan aktif\n"
            "• /myalerts — alert terpasang\n"
            "• /performance — performa trading\n"
            "• `/feedback TLKM 5` — rating analisa\n\n"
            "━━━━━━━━━━━━━━━━━\n"
            "🎁 *Baru?* Coba Premium gratis 7 hari: /pricing"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def pricing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton("💎 Pro Rp49k/bln", callback_data="sub_pro"),
                InlineKeyboardButton("👑 Premium Rp149k/bln", callback_data="sub_premium"),
            ],
            [
                InlineKeyboardButton("🌟 Lifetime Rp1.999k", callback_data="sub_lifetime"),
                InlineKeyboardButton("🏢 White-label", callback_data="sub_whitelabel"),
            ],
        ]
        text = (
            "💰 *Langganan Vilona Saham*\n\n"
            "━━━━━━━━━━━━━━━━━\n"
            "📊 *Free — Rp0*\n"
            "• 5 screening/hari\n"
            "• Watchlist 3 saham\n"
            "• Data delay 15 menit\n"
            "• 5 alert\n\n"
            "💎 *Pro — Rp49.000/bulan*\n"
            "• ✅ Unlimited screening\n"
            "• ✅ Watchlist 10 saham\n"
            "• ✅ 50 alert\n"
            "• ✅ Real-time data\n"
            "• ✅ AI trade setup\n\n"
            "👑 *Premium — Rp149.000/bulan*\n"
            "• ✅ Semua Pro + 200 alert\n"
            "• ✅ Bandar View + Market Sentiment\n"
            "• ✅ Sector Forecast (11 sektor, 7 hari)\n"
            "• ✅ Event Classifier (11 kelas korporat)\n"
            "• ✅ Auto-Report Mingguan (Senin pagi)\n"
            "• ✅ Watchlist Smart + daily digest\n"
            "• ✅ Priority response\n\n"
            "🌟 *Lifetime — Rp1.999.000*\n"
            "• Akses selamanya (sisa 998 seat)\n\n"
            "🏢 *White-label — Rp5jt + Rp500rb/bln*\n"
            "• Branding sendiri + panel admin\n"
            "• Jual ke komunitas lo\n\n"
            "━━━━━━━━━━━━━━━━━\n"
            "🎁 *Baru?* GRATIS 7 hari Premium — klik tombol di bawah\n"
            "💡 Sudah 3.000+ analisa dihasilkan oleh trader lain"
        )
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    # ── Analyze ──

    async def analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
        if not symbol:
            await update.message.reply_text("Masukkan kode saham. Contoh: `analisa TLKM`")
            return

        symbol = symbol.upper()
        await update.message.reply_text(
            f"🔍 Menganalisa *{symbol}*... (mohon tunggu 10-15 detik)",
            parse_mode="Markdown",
        )

        # ─── Engines ──────────────────────────────────────────
        from src.engine.technical import TechnicalEngine
        from src.engine.fundamental import FundamentalEngine
        from src.engine.broker_flow import BrokerFlowEngine

        tech = TechnicalEngine()
        funda = FundamentalEngine()
        flow = BrokerFlowEngine()

        # ─── Technical via iTick ──────────────────────────────
        feed = await self._get_feed()
        quote_raw = await feed.get_quote(symbol)
        klines_raw = await feed.get_klines(symbol, "1d", 100)

        # Normalize: support both dict and object returns
        price = change = 0.0
        tech_analysis = {}
        tech_score = 5
        tech_reasons = ["Data terbatas"]

        # Get price from quote
        if quote_raw and isinstance(quote_raw, dict):
            price = float(quote_raw.get("price", 0))
            change = float(quote_raw.get("change_pct", 0))
        elif quote_raw and hasattr(quote_raw, "price"):
            price = float(quote_raw.price)
            change = getattr(quote_raw, "change_pct", 0) or 0

        # Parse klines (list of dict)
        klines = []
        for k in (klines_raw or []):
            if isinstance(k, dict):
                klines.append(k)
            elif hasattr(k, "close"):
                klines.append({"open": k.open, "high": k.high, "low": k.low,
                               "close": k.close, "volume": k.volume, "timestamp": getattr(k, "timestamp", 0)})

        if len(klines) > 20:
            closes = [float(k["close"]) for k in klines]
            highs = [float(k["high"]) for k in klines]
            lows = [float(k["low"]) for k in klines]
            volumes = [int(k["volume"]) for k in klines]

            try:
                tech_analysis = tech.analyze(symbol, closes, highs, lows, volumes)
                tech_score, tech_reasons = tech.combined_score(closes, highs, lows, volumes)
                if change == 0 and len(closes) >= 5:
                    change = ((price - closes[-1]) / closes[-1] * 100)
            except Exception:
                tech_analysis = {"symbol": symbol, "price": price, "indicators": {}}
                tech_score = 5
                tech_reasons = ["Error analisa"]

        # ─── Fundamental via yfinance ─────────────────────────
        funda_data = None
        try:
            funda_data = await funda.fetch(symbol)
        except Exception:
            pass

        # ─── Foreign Flow via Infovesta API ───────────────────
        flow_data = None
        try:
            flow_data = await flow.get_foreign_flow(symbol)
        except Exception:
            pass

        # ─── Broker Flow via RapidAPI IDX (NEW) ────────────────
        rapidapi_broker = None
        try:
            from src.feed.rapidapi_idx import RapidAPIFeed
            rfeed = RapidAPIFeed()
            rapidapi_broker = await rfeed.get_broker_flow_summary()
            await rfeed.close()
        except Exception:
            pass

        # ─── News Sentiment ───────────────────────────────────
        news_data = None
        try:
            from src.engine.news import NewsEngine
            news_engine = NewsEngine(max_days=30, max_articles=3)
            news_data = await news_engine.analyze(symbol)
        except Exception:
            pass

        # ─── AI Analysis via OmniRoute ──────────────────────────
        ai_insight = None
        try:
            from src.engine.ai_analysis import analyze_with_ai, set_learning_context
            from src.engine.learning import format_learning_context

            # Inject learning from past analyses
            learning = format_learning_context(symbol)
            if learning:
                set_learning_context(learning)

            funda_dict = {
                "per": getattr(funda_data, "per", 0),
                "pbv": getattr(funda_data, "pbv", 0),
                "roe": getattr(funda_data, "roe", 0),
            } if funda_data else None

            flow_dict = {
                "net_buy": getattr(flow_data, "net_buy", 0),
                "streak_days": getattr(flow_data, "streak_days", 0),
            } if flow_data else None

            # Merge RapidAPI broker data into flow_dict
            if rapidapi_broker:
                if flow_dict is None:
                    flow_dict = {}
                flow_dict["market_foreign_net"] = rapidapi_broker.get("foreign_net_buy", 0)
                flow_dict["foreign_ratio"] = rapidapi_broker.get("foreign_domestic_ratio", 0) * 100

            news_list = [
                {"sentiment": getattr(a, "sentiment", "neutral")}
                for a in (getattr(news_data, "articles", None) or [])
            ] if news_data else None

            ai_insight = await analyze_with_ai(
                symbol=symbol,
                price=price,
                change_pct=change,
                technical_data=tech_analysis,
                fundamental_data=funda_dict,
                foreign_flow_data=flow_dict,
                news_data=news_list,
                score=tech_score,
            )
        except Exception:
            pass

        # ─── Build Output ─────────────────────────────────────
        if price == 0:
            await update.message.reply_text(f"❌ Data untuk {symbol} tidak ditemukan.")
            return

        emoji = "🟢" if change >= 0 else "🔴"

        text = f"{emoji} *{symbol}* — Rp{price:,.0f} ({change:+.1f}%)\n\n"

        # Technical section
        text += "📊 *Teknikal:*\n"
        ind = tech_analysis.get("indicators", {})
        analysis_body = tech_analysis.get("analysis", {})

        rsi = ind.get("RSI14", analysis_body.get("rsi"))
        if rsi:
            signal = "oversold" if rsi < 30 else ("overbought" if rsi > 70 else "netral")
            rsi_emoji = "🟢" if rsi < 30 else ("🔴" if rsi > 70 else "➖")
            text += f"  {rsi_emoji} RSI(14): {rsi:.1f} ({signal})\n"

        macd = ind.get("MACD", analysis_body.get("macd", {}))
        if isinstance(macd, dict) and "trend" in macd:
            macd_emoji = "🟢" if macd["trend"] == "golden cross" else ("🔴" if macd["trend"] == "death cross" else "➖")
            text += f"  {macd_emoji} MACD: {macd['trend']}\n"

        bb = ind.get("Bollinger", analysis_body.get("bollinger", {}))
        if isinstance(bb, dict) and "position" in bb:
            pos = bb["position"]
            bb_emoji = "🟢" if pos == "below lower" else ("🔴" if pos == "above upper" else "➖")
            text += f"  {bb_emoji} Bollinger: {pos}\n"

        st = ind.get("SuperTrend", analysis_body.get("super_trend", {}))
        if isinstance(st, dict) and "trend" in st:
            st_emoji = "🟢" if st["trend"] == "up" else "🔴"
            text += f"  {st_emoji} SuperTrend: {st['trend']}\n"

        vol = ind.get("Volume", analysis_body.get("volume", {}))
        if isinstance(vol, dict) and vol.get("spike"):
            text += f"  🔥 Volume: SPIKE ({vol.get('latest', 0):,})\n"

        vol_profile = analysis_body.get("volume_profile", {})
        if vol_profile:
            if vol_profile.get("above_sma20"):
                text += f"  📈 Volume di atas SMA20 ({vol_profile['above_sma20']}x)\n"

        # Fundamental section
        text += "\n🏢 *Fundamental:*\n"
        if funda_data and funda_data.per > 0:
            text += f"  PER: {funda_data.per:.1f}x | PBV: {funda_data.pbv:.2f}x\n"
            text += f"  ROE: {funda_data.roe:.1f}% | DER: {funda_data.der:.1f}\n"
            text += f"  M.Cap: {funda_data._format_billion(funda_data.market_cap)}\n"
            if funda_data.dividend_yield > 0:
                text += f"  Div Yield: {funda_data.dividend_yield:.2f}%\n"
            if funda_data.revenue_growth != 0:
                text += f"  Revenue Growth: {funda_data.revenue_growth:+.1f}%\n"
        else:
            text += "  Data fundamental tidak tersedia\n"

        # Foreign Flow section
        text += "\n🏦 *Foreign Flow:*\n"
        if flow_data and flow_data.net_buy != 0:
            dir_emoji = "🟢" if flow_data.is_net_buy() else "🔴"
            dir_text = "NET BUY" if flow_data.is_net_buy() else "NET SELL"
            text += f"  {dir_emoji} {dir_text}: Rp{abs(flow_data.net_buy):,.0f}\n"
            text += f"  Buy: Rp{flow_data.foreign_buy:,.0f} | Sell: Rp{flow_data.foreign_sell:,.0f}\n"
            if flow_data.streak_days > 0:
                text += f"  Streak: {flow_data.streak_days} hari\n"
        elif rapidapi_broker:
            fnb = rapidapi_broker.get("foreign_net_buy", 0)
            if fnb != 0:
                dir_emoji = "🟢" if fnb > 0 else "🔴"
                dir_text = "NET BUY" if fnb > 0 else "NET SELL"
                text += f"  {dir_emoji} {dir_text} Asing: Rp{abs(fnb):,.0f}\n"
                text += f"  Buy: Rp{rapidapi_broker.get('foreign_buy',0):,.0f} | Sell: Rp{rapidapi_broker.get('foreign_sell',0):,.0f}\n"
                text += f"  Foreign Ratio: {rapidapi_broker.get('foreign_domestic_ratio',0)*100:.1f}%\n"
            else:
                text += "  Asing net flat hari ini\n"
        else:
            text += "  Tidak ada aktivitas asing signifikan hari ini\n"

        # News section
        text += "\n📰 *Berita:*\n"
        if news_data and news_data.articles:
            for a in news_data.articles[:3]:
                emoji = "🟢" if a.sentiment == "positive" else ("🔴" if a.sentiment == "negative" else "⚪")
                short = a.title[:65] + "..." if len(a.title) > 65 else a.title
                text += f"  {emoji} {short}\n"
            text += f"  *{news_data.summary}*\n"
        else:
            text += "  Tidak ada berita terkini\n"

        # AI Insight section
        if ai_insight:
            text += f"\n🧠 *AI Insight:*\n  {ai_insight}\n"

        # Score & Signal
        # Build final score: technical + fundamental bonuses
        final_score = tech_score
        final_reasons = list(tech_reasons[:2])

        if funda_data and funda_data.per > 0:
            if 5 <= funda_data.per <= 15:
                final_score = min(final_score + 1, 10)
                final_reasons.append("Fundamental OK")
            if funda_data.roe >= 15:
                final_score = min(final_score + 1, 10)
                final_reasons.append("ROE kuat")
            if funda_data.is_undervalued():
                final_score = min(final_score + 1, 10)
                final_reasons.append("Undervalued")

        if flow_data and flow_data.is_net_buy():
            final_score = min(final_score + 1, 10)

        signal_emoji = "🟢" if final_score >= 7 else ("🟡" if final_score >= 5 else "🔴")
        signal_text = "BUY" if final_score >= 7 else ("WATCH" if final_score >= 5 else "PASS")

        # ─── Record to Analysis Journal ────────────────────────
        try:
            from datetime import datetime
            import json, hashlib, os
            db = await self._get_db()
            aid = hashlib.md5(f"{symbol}{datetime.utcnow().isoformat()}{os.urandom(4).hex()}".encode()).hexdigest()[:16]
            indicators = {
                "rsi": ind.get("rsi", analysis_body.get("rsi")),
                "macd": ind.get("macd_signal", analysis_body.get("macd", {}).get("signal")),
                "volume_spike": vol.get("spike") if isinstance(vol, dict) else None,
                "trend": st.get("trend") if st else analysis_body.get("super_trend", {}).get("trend"),
            }
            bias = "BULLISH" if final_score >= 7 else ("BEARISH" if final_score <= 4 else "NEUTRAL")
            entry = AnalysisJournal(
                analysis_id=aid,
                symbol=symbol,
                price_at_analysis=price,
                signal=signal_text,
                score=final_score,
                ai_insight=ai_insight or "",
                key_indicators=json.dumps(indicators),
                bias=bias,
            )
            db.add(entry)
            await db.commit()
        except Exception as e:
            logger.warning(f"Journal record failed: {e}")

        # ─── Generate Chart (clean TradingView, no overlay) ─────
        chart_sent = False
        klines = None
        zones = None
        tech_indicators = None
        try:
            from src.visual import download_chart

            chart_path = await download_chart(
                symbol=symbol,
                studies=["Volume", "MACD"],
            )
            if chart_path:
                with open(chart_path, "rb") as f:
                    caption = (
                        f"{signal_emoji} *{symbol}* — Rp{price:,.0f} ({change:+.1f}%)  |  "
                        f"📊 *{final_score}/10* — *{signal_text}*"
                    )
                    await update.message.reply_photo(
                        photo=f, caption=caption, parse_mode="Markdown",
                    )
                chart_sent = True
                try:
                    chart_path.unlink()
                except Exception:
                    pass

                # ─── Fetch klines for zone + indicator text ─────
                try:
                    klines = await feed.get_klines(symbol, interval="1d", limit=90)
                    if klines:
                        from src.engine.zone_finder import ZoneFinder
                        from src.engine.technical import TechnicalEngine
                        closes = [k["close"] for k in klines]
                        highs = [k["high"] for k in klines]
                        lows = [k["low"] for k in klines]
                        volumes = [k["volume"] for k in klines]
                        zf = ZoneFinder()
                        zones = zf.find_levels(klines, price)
                        te = TechnicalEngine()
                        tech_indicators = te.analyze(symbol, closes, highs, lows, volumes)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"TradingView chart failed: {e}")

        # ─── Final analysis text (zones + indicators + signal) ─
        out = ""
        if zones and tech_indicators:
            ind = tech_indicators.get("indicators", {})
            rsi_val = ind.get("RSI14", "—")
            rsi_str = f"{rsi_val:.1f}" if isinstance(rsi_val, float) else str(rsi_val)
            macd_data = ind.get("MACD", {})
            macd_trend = macd_data.get("trend", "—")
            macd_emoji = "🟢" if macd_trend == "bullish" else ("🔴" if macd_trend == "bearish" else "⚪")
            sma20 = ind.get("SMA20", 0)
            sma50 = ind.get("SMA50", 0)
            vol = ind.get("Volume", {})
            vol_status = "🔺 Spike" if vol.get("spike") else "▶ Normal"
            bollinger = ind.get("Bollinger", {})
            bb_pos = bollinger.get("position", "")
            bb_str = f"  │  Bollinger: {bb_pos}" if bb_pos else ""

            out += (
                f"📍 *Zone Mapping*\n"
                f"🔴 R: Rp{zones['resistance']:,.0f}    🟢 S: Rp{zones['support']:,.0f}\n"
                f"🎯 Entry: Rp{zones['entry_zone_low']:,.0f} - Rp{zones['entry_zone_high']:,.0f}\n"
                f"\n📊 *Indikator*\n"
                f"RSI: {rsi_str}  │  MACD: {macd_emoji} {macd_trend}\n"
                f"SMA20: {sma20:,.0f}  │  SMA50: {sma50:,.0f}\n"
                f"Vol: {vol_status}{bb_str}\n"
            )
            if flow_data:
                net = getattr(flow_data, "net_buy", 0)
                streak = getattr(flow_data, "streak_days", 0)
                if net:
                    direction = "Buy" if net > 0 else "Sell"
                    ftext = f"🏦 Net {direction} Rp{abs(net):,.0f}"
                    ftext += f" ({streak}d)" if streak else ""
                    out += f"\n{ftext}\n"
            elif rapidapi_broker:
                fnb = rapidapi_broker.get("foreign_net_buy", 0)
                fbo = rapidapi_broker.get("foreign_domestic_ratio", 0) * 100
                if fnb:
                    direction = "Buy" if fnb > 0 else "Sell"
                    out += f"\n🏦 Foreign Net {direction}: Rp{abs(fnb):,.0f} ({fbo:.1f}% foreign)\\n"

        out += f"\n{signal_emoji} *Score: {final_score}/10*  —  *{signal_text}*\n"
        if final_reasons:
            out += f"_{', '.join(final_reasons)}_\n"
        if ai_insight:
            out += f"\n🧠 *AI:*  {ai_insight}\n"

        # ─── Bandarmology + Sentiment (RapidAPI powered) ───────
        if rapidapi_broker:
            out += f"\n🎰 *Bandarmology:*\n"
            fnb = rapidapi_broker.get("foreign_net_buy", 0)
            fbr = rapidapi_broker.get("foreign_domestic_ratio", 0) * 100
            if fnb > 200_000_000_000:
                out += f"  🟢 Akumulasi Asing: Rp{fnb:,.0f} ({fbr:.1f}% foreign)\n"
            elif fnb < -200_000_000_000:
                out += f"  🔴 Distribusi Asing: Rp{abs(fnb):,.0f}\n"
            else:
                out += f"  ⚪ Netral: Rp{fnb:,.0f}\n"

            # Top broker
            top_brokers = rapidapi_broker.get("top_brokers", [])
            foreign_brokers = [b for b in top_brokers if b.get("group") == "BROKER_GROUP_FOREIGN"]
            if foreign_brokers:
                top = foreign_brokers[0]
                out += f"  🔝 {top['code']} {top['name']}: Net Rp{float(top['net_value']):,.0f}\n"

        out += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Ketik `analisa BBCA` atau `screener asing 3 hari`\n"
            f"💎 /pricing — real-time + 50 alert + analisa lebih dalam"
        )

        # Add share button
        keyboard = [[InlineKeyboardButton(
            "📤 Share Analisa",
            callback_data=f"share_an_{symbol}_{final_score}_{signal_text}"
        )]]
        await update.message.reply_text(
            out, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ── My Plans ──

    async def myplans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            db = await self._get_db()
            from src.engine.plan import TradePlanEngine
            from src.services.user_manager import UserManager

            um = UserManager(db)
            user = await um.get_or_create_user(update.effective_user.id)
            planner = TradePlanEngine(db)

            active = await planner.get_user_plans(user.id, "active")
            won = await planner.get_user_plans(user.id, "hit_tp")
            lost = await planner.get_user_plans(user.id, "hit_sl")

            if not active and not won and not lost:
                text = (
                    "📋 *Trading Plan*\n\n"
                    "Belum ada plan. Buat dengan:\n"
                    "`plan TLKM entry 4600 sl 4500 tp 4800`\n\n"
                    "💡 Bot auto-report plan lo — notifikasi waktu kena SL/TP."
                )
            else:
                text = "📋 *Trading Plan*\n━━━━━━━━━━━━━━━━━\n"
                if active:
                    text += f"\n*🟡 Aktif ({len(active)}):*\n"
                    for p in active[:5]:
                        text += f"  • {p.symbol}: Entry Rp{p.entry_price:,.0f} | SL Rp{p.stop_loss or '?'} | TP Rp{p.take_profit or '?'}\n"
                if won:
                    text += f"\n*✅ Menang ({len(won)}):*\n"
                    for p in won[:3]:
                        profit = abs(p.take_profit - p.entry_price) if p.take_profit else 0
                        text += f"  • {p.symbol}: +Rp{profit:,.0f}\n"
                if lost:
                    text += f"\n*❌ Kalah ({len(lost)}):*\n"
                    for p in lost[:3]:
                        loss = abs(p.entry_price - p.stop_loss) if p.stop_loss else 0
                        text += f"  • {p.symbol}: -Rp{loss:,.0f}\n"
                if active and len(active) >= 5:
                    text += "\n💎 Pro: unlimited plan — /pricing"
                else:
                    text += "\n📊 Cek performa: /performance"
        except Exception as e:
            text = f"❌ Error: {str(e)[:100]}"
        await update.message.reply_text(text, parse_mode="Markdown")

    # ── My Alerts ──

    async def myalerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            db = await self._get_db()
            from src.engine.alerter import AlertEngine
            from src.services.user_manager import UserManager

            um = UserManager(db)
            user = await um.get_or_create_user(update.effective_user.id)
            alerter = AlertEngine(db)
            alerts = await alerter.get_user_alerts(user.id)

            if not alerts:
                text = (
                    "🔔 *Alert Harga*\n\n"
                    "Belum ada alert. Buat dengan:\n"
                    "`alert TLKM >4600` atau `alert BBCA <5800`\n\n"
                    "💎 Upgrade Pro untuk 50 alert: /pricing"
                )
            else:
                text = f"🔔 *Alert Aktif ({len(alerts)})*\n━━━━━━━━━━━━━━━━━\n"
                for a in alerts[:20]:
                    arrow = "🟢" if a.condition == ">" else "🔴"
                    status = "✅ triggered" if a.is_triggered else "⏳ menunggu"
                    text += f"{arrow} {a.symbol} {a.condition} Rp{a.value:,.0f} — {status}\n"
                if len(alerts) >= 20:
                    text += "\n💎 Pro: 50 alert — /pricing"
                else:
                    text += "\n➕ Buat alert baru: `alert TLKM <harga>`"
        except Exception as e:
            text = f"❌ Error: {str(e)[:100]}"
        await update.message.reply_text(text, parse_mode="Markdown")

    # ── Performance Stats ──

    async def performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            db = await self._get_db()
            from src.engine.plan import TradePlanEngine
            from src.services.user_manager import UserManager

            um = UserManager(db)
            user = await um.get_or_create_user(update.effective_user.id)
            planner = TradePlanEngine(db)
            perf = await planner.get_performance(user.id)

            wr_color = "🟢" if perf["win_rate"] >= 60 else ("🟡" if perf["win_rate"] >= 40 else "🔴")
            total_pnl = perf.get("total_pnl", 0)
            pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
            text = (
                f"📊 *Performa Trading*\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"Total: {perf['total_trades']} trades\n"
                f"Win: {perf['wins']} | Lose: {perf['losses']}\n"
                f"{wr_color} Win Rate: {perf['win_rate']}%\n"
                f"{pnl_emoji} P&L: Rp{abs(total_pnl):,.0f}\n"
                f"Aktif: {perf['active']} plan\n\n"
                f"📋 Detail plan: /myplans\n"
                f"💡 Akurasi AI mingguan: kirim `analisa TLKM` sekarang"
            )
        except Exception as e:
            text = (
                "📊 *Performa Trading*\n\n"
                "Gunakan `plan` dulu untuk memulai trading.\n"
                "Contoh: `plan TLKM entry 4600 sl 4500 tp 4800`"
            )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        cmd = self.nlp.parse(text)

        if cmd.intent == Intent.ANALYZE:
            try:
                await self.analyze(update, context, cmd.symbol)
            except Exception as e:
                logger.error(f"Analyze failed: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Gagal menganalisa: {str(e)[:100]}"
                )
        elif cmd.intent == Intent.SCREEN:
            rules = cmd.params.get('rules', ['technical', 'fundamental', 'foreign_flow'])
            # Use all available IDX stocks (from encyclopedia)
            try:
                from src.engine.idx_encyclopedia import all_stocks
                symbols = list(all_stocks().keys())
            except Exception:
                symbols = ['BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII', 'ADRO', 'UNVR', 
                          'ICBP', 'INDF', 'PTBA', 'ANTM', 'GGRM', 'HMSP', 'UNTR',
                          'KLBF', 'PGAS', 'SMGR', 'CPIN', 'AMRT', 'ACES', 'BRIS',
                          'TOWR', 'EXCL', 'ISAT', 'MTEL', 'BUKA', 'GOTO', 'EMTK', 'MDKA']
            await update.message.reply_text(
                f"🔍 Screening {len(symbols)} saham... (mohon tunggu 30-60 detik)",
            )
            try:
                from src.engine.screener import ScreenerEngine
                se = ScreenerEngine()
                results = await se.screen(symbols, rules, min_score=3)
                if results:
                    text = "📊 *Hasil Screening*\n\n"
                    for r in results:
                        score_emoji = "🟢" if r['score'] >= 7 else ("🟡" if r['score'] >= 5 else "🔴")
                        text += (
                            f"{score_emoji} {r['symbol']} — *{r['signal']}* ({r['score']}/10)\n"
                            f"  {' · '.join(r['reasons'][:2])}\n\n"
                        )
                    text += (
                        "━━━━━━━━━━━━━━━━━\n"
                        "💎 *Pro* lihat detail lengkap tiap saham: upgrade /pricing"
                    )
                else:
                    text = (
                        "📊 *Hasil Screening*\n\n"
                        "Tidak ada saham yang lolos filter saat ini.\n\n"
                        "Coba kriteria lain: `screener volume spike` atau `screener akumulasi asing 3 hari`"
                    )
            except Exception as e:
                text = f"❌ Screening error: {str(e)[:100]}"
            await update.message.reply_text(text, parse_mode="Markdown")
        elif cmd.intent == Intent.BRIEFING:
            try:
                await self.briefing(update, context)
            except Exception as e:
                logger.error(f"Briefing failed: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Gagal briefing: {str(e)[:100]}"
                )
        elif cmd.intent == Intent.NEWS:
            # Route to news handler with symbol
            context.args = [cmd.symbol] if cmd.symbol else []
            await self.news(update, context)
        elif cmd.intent == Intent.TRENDING:
            await self.trending(update, context)
        elif cmd.intent == Intent.PLAN:
            try:
                db = await self._get_db()
                from src.engine.plan import TradePlanEngine
                from src.services.user_manager import UserManager
                from src.models import User

                um = UserManager(db)
                user = await um.get_or_create_user(
                    update.effective_user.id,
                    update.effective_user.username or "",
                    update.effective_user.full_name or "",
                )

                entry = cmd.params.get('entry')
                sl = cmd.params.get('sl')
                tp = cmd.params.get('tp')
                if not entry or not sl:
                    text = "Format: `plan TLKM entry 4600 sl 4500 tp 4800`"
                else:
                    notes_text = cmd.params.get('reason', '')
                    planner = TradePlanEngine(db)
                    plan = await planner.create_plan(
                        user.id, cmd.symbol,
                        entry_price=float(entry if entry != '?' else 0),
                        stop_loss=float(sl if sl != '?' else 0),
                        take_profit=float(tp) if tp and tp != '?' else None,
                        notes=notes_text,
                    )
                    if plan:
                        text = (
                            f"📋 *Trading Plan Tersimpan* — {cmd.symbol}\n"
                            f"Entry: Rp{plan.entry_price:,.0f}\n"
                            f"SL: Rp{plan.stop_loss:,.0f}\n"
                            f"TP: Rp{plan.take_profit:,.0f} "
                            f"({'✅' if plan.risk_reward >= 2 else '🟡' if plan.risk_reward >= 1.5 else '⚠️'} R/R: {plan.risk_reward}x)\n\n"
                            "Auto-report aktif — saya akan kirim notifikasi jika harga menyentuh SL/TP.\n"
                            "📊 Pantau performa: /performance"
                        )
                        # Also show risk calculation
                        from src.engine.risk import RiskManager
                        rm = RiskManager()
                        capital = getattr(user, 'capital', None) or 10_000_000
                        sizing = rm.calculate_position(
                            cmd.symbol, capital,
                            plan.entry_price, plan.stop_loss, plan.take_profit,
                        )
                        text += f"\n\n{rm.format_sizing(sizing)}"
                    else:
                        text = "❌ Gagal menyimpan trading plan."
            except Exception as e:
                text = f"❌ Error: {str(e)[:100]}"
            await update.message.reply_text(text, parse_mode="Markdown")
        elif cmd.intent == Intent.ALERT:
            try:
                db = await self._get_db()
                from src.engine.alerter import AlertEngine
                from src.services.user_manager import UserManager

                um = UserManager(db)
                user = await um.get_or_create_user(
                    update.effective_user.id,
                    update.effective_user.username or "",
                    update.effective_user.full_name or "",
                )

                operator = cmd.params.get('operator', '>')
                value = cmd.params.get('value', 0)
                if not cmd.symbol or not value:
                    text = "Format: `alert TLKM >4600` atau `alert BBCA <5800`"
                else:
                    alerter = AlertEngine(db)
                    alert = await alerter.create_alert(
                        user.id, cmd.symbol,
                        condition=operator, value=float(value),
                    )
                    if alert:
                        active = await alerter.get_active_count(user.id)
                        limit = 5 if user.tier == "free" else (50 if user.tier == "pro" else 200)
                        text = (
                            f"🔔 *Alert Terpasang* — {cmd.symbol}\n"
                            f"Kondisi: {alert.symbol} {alert.condition} Rp{alert.value:,.0f}\n"
                            f"Alert aktif: {active}/{limit}\n\n"
                            f"Saya akan kirim notifikasi saat harga memenuhi kondisi.\n"
                            f"📋 Cek alert: /myalerts"
                        )
                    else:
                        text = "❌ Kuota alert penuh! Upgrade untuk menambah alert.\n/pricing"
            except Exception as e:
                text = f"❌ Error: {str(e)[:100]}"
            await update.message.reply_text(text, parse_mode="Markdown")
        elif cmd.intent == Intent.STATS:
            # Simple stats from feed
            feed = await self._get_feed()
            quote = await feed.get_quote(cmd.symbol)
            if quote:
                chg_emoji = "🟢" if getattr(quote, "change_pct", 0) >= 0 else "🔴"
                text = (
                    f"📈 *Statistik {cmd.symbol}*\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"Harga: Rp{quote.price:,.0f} {chg_emoji}\n"
                    f"High: Rp{quote.high:,.0f}\n"
                    f"Low: Rp{quote.low:,.0f}\n"
                    f"Volume: {quote.volume:,}\n"
                    f"Nilai: Rp{quote.value:,.0f}\n\n"
                    f"💡 Analisa lengkap: `analisa {cmd.symbol}`"
                )
            else:
                text = (
                    f"❌ Data untuk {cmd.symbol} tidak tersedia.\n\n"
                    "Coba: `stats BBCA` atau `analisa TLKM`"
                )
            await update.message.reply_text(text, parse_mode="Markdown")
        elif cmd.intent == Intent.BACKTEST:
            symbol = cmd.symbol or "BBCA"
            await update.message.reply_text(
                f"📊 Backtesting {symbol}... (mohon tunggu 30-60 detik)",
            )
            try:
                from src.engine.idx_backtest import BacktestEngine
                engine = BacktestEngine(years=3)
                r = await engine.validate(symbol)
                if r and r.total_signals > 0:
                    text = (
                        f"📊 *Backtest — {symbol} ({r.name})*\n"
                        f"Periode: {r.years_analyzed:.1f} tahun | {r.data_points} hari\n\n"
                        f"*📈 Performa:*\n"
                        f"• Sinyal: *{r.total_signals}*\n"
                        f"• Win Rate: *{r.win_rate:.1%}*\n"
                        f"• Avg Return: *{r.avg_return:+.1f}%*\n"
                        f"• Max: {r.max_return:+.1f}% | Min: {r.min_return:+.1f}%\n\n"
                        f"*⏱ Akurasi:*\n"
                        f"• H+1: *{r.h1_accuracy:.1%}*\n"
                        f"• H+3: *{r.h3_accuracy:.1%}*\n"
                        f"• H+5: *{r.h5_accuracy:.1%}*\n\n"
                        f"*⚠️ Risk:*\n"
                        f"• Sharpe: {r.sharpe_ratio:.2f}\n"
                        f"• Max DD: {r.max_drawdown:.1f}%\n"
                        f"• Profit Factor: {r.profit_factor:.2f}\n\n"
                        f"*📊 vs Buy & Hold:*\n"
                        f"• Buy&Hold: {r.buy_hold_return:+.1f}%\n"
                        f"• Strategy: {r.strategy_return:+.1f}%\n"
                        f"• Alpha: {r.alpha:+.1f}%\n\n"
                        "━━━━━━━━━━━━━━━━━\n"
                        "⚠️ Backtest tidak menjamin hasil masa depan\n\n"
                        f"📤 *Bagikan:* forward pesan ini ke grup trader kamu"
                    )
                    # Add share button
                    keyboard = [[InlineKeyboardButton(
                        "📤 Share Card",
                        callback_data=f"share_bt_{symbol}_{r.win_rate:.0%}_{r.sharpe_ratio:.1f}"
                    )]]
                    await update.message.reply_text(
                        text, parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                    return
                else:
                    text = f"⚠️ Data tidak cukup untuk backtest {symbol}."
            except Exception as e:
                text = f"❌ Backtest error: {str(e)[:100]}"
            await update.message.reply_text(text, parse_mode="Markdown")
        elif cmd.intent == Intent.HELP:
            await self.help(update, context)
        elif cmd.intent == Intent.PRICING:
            await self.pricing(update, context)
        else:
            await update.message.reply_text(
                "🤔 *Perintah tidak dikenali*\n\n"
                "Coba:\n"
                "• `analisa TLKM` — analisa saham\n"
                "• `screener akumulasi asing` — screening\n"
                "• `plan TLKM entry 4600 sl 4500 tp 4800` — plan\n"
                "• /help — bantuan lengkap\n\n"
                "Atau kirim kode saham langsung — `TLKM` aja cukup.",
                parse_mode="Markdown",
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data
        if data == "sub_pro":
            text = (
                "💎 *Pro — Rp49.000/bulan*\n\n"
                "✅ Unlimited screening & analisa\n"
                "✅ Watchlist 10 saham\n"
                "✅ Real-time data\n"
                "✅ 50 alert otomatis\n"
                "✅ AI trade setup\n\n"
                "📲 Link pembayaran akan dikirim ke chat ini.\n"
                "💡 Sudah 3.000+ analisa dihasilkan."
            )
        elif data == "sub_premium":
            text = (
                "👑 *Premium — Rp149.000/bulan*\n\n"
                "✅ Semua fitur Pro\n"
                "✅ Bandar View + Market Sentiment\n"
                "✅ Sector Forecast 11 sektor\n"
                "✅ Event Classifier korporat\n"
                "✅ Auto-Report Mingguan (Senin pagi)\n"
                "✅ Prioritas AI response\n\n"
                "🎁 *GRATIS 7 hari* — kalo gak cocok refund full.\n"
                "📲 Link pembayaran akan dikirim ke chat ini."
            )
        elif data == "sub_lifetime":
            text = (
                "🌟 *Lifetime — Rp1.999.000*\n\n"
                "Akses premium selamanya.\n"
                "Sisa 998 dari 1000 seat.\n\n"
                "📲 Link pembayaran akan dikirim ke chat ini.\n"
                "💡 Begitu 1000 seat habis, harga naik."
            )
        elif data.startswith("share_bt_"):
            # Backtest share card
            parts = data.split("_")
            symbol = parts[2] if len(parts) > 2 else "?"
            wr = parts[3] if len(parts) > 3 else "?"
            sharpe = parts[4].replace(".", ",") if len(parts) > 4 else "?"
            text = (
                f"📊 *Backtest {symbol}* — Generated by @vilonidxbot\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Win Rate: *{wr}* | Sharpe: *{sharpe}*\n\n"
                f"🔍 Coba sendiri: t.me/vilonidxbot\n"
                f"💎 Upgrade Premium: /pricing\n\n"
                f"#IDX #Saham #{symbol} #TradingBot"
            )
            await query.edit_message_text(text, parse_mode="Markdown")
            return
        elif data.startswith("share_an_"):
            # Analisa share card
            parts = data.split("_")
            symbol = parts[2] if len(parts) > 2 else "?"
            score = parts[3] if len(parts) > 3 else "?"
            signal = parts[4] if len(parts) > 4 else "?"
            text = (
                f"📊 *Analisa {symbol}* — Generated by @vilonidxbot\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Score: *{score}/10* → *{signal}*\n\n"
                f"🔍 Analisa saham IDX gratis: t.me/vilonidxbot\n"
                f"🧠 AI + Bandar Flow + Fundamental\n\n"
                f"#IDX #Saham #{symbol} #TradingBot #AI"
            )
            await query.edit_message_text(text, parse_mode="Markdown")
            return
        elif data == "sub_whitelabel":
            text = (
                "🏢 *White-label*\n\n"
                "• Setup: Rp5.000.000\n"
                "• Bulanan: Rp500.000\n"
                "• Branding sendiri + panel admin\n"
                "• Jual ke komunitas lo\n\n"
                "Hubungi admin untuk demo."
            )
        else:
            text = "Pilihan tidak valid."

        # Add feedback CTA at bottom
        text += "\n\n📌 Ada pertanyaan? Kirim aja langsung."

        await query.edit_message_text(text, parse_mode="Markdown")

    # ── News ──

    async def report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate weekly market report on demand."""
        msg = await update.message.reply_text("📊 Menyusun laporan mingguan... (30 detik)")
        try:
            from src.engine.weekly_report import generate_weekly_report
            report = await generate_weekly_report()
            await msg.edit_text(report, parse_mode="Markdown")
        except Exception as e:
            await msg.edit_text(
                f"❌ Gagal membuat laporan: {str(e)[:100]}\n\nCoba lagi nanti."
            )

    async def trending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trending stocks (weekly momentum)."""
        msg = await update.message.reply_text("🔥 Menganalisa tren 39 saham IDX... (60-90 detik)")
        try:
            from src.engine.trending import analyze_trending, format_trending
            report = await analyze_trending()
            card = format_trending(report)
            await msg.edit_text(card, parse_mode="Markdown")
        except Exception as e:
            await msg.edit_text(
                f"❌ Gagal menganalisa tren: {str(e)[:100]}\n\nCoba lagi nanti."
            )

    # ── News ──

    async def news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Fetch latest news for a stock symbol.
        Usage: /news TLKM or /news (general market news)
        """
        args = context.args or []
        symbol = args[0].upper() if args else ""

        if not symbol:
            # General market news from ingestion pipeline
            msg = await update.message.reply_text("📰 Mencari berita pasar terbaru...")
            try:
                from src.ingestion import scrape_all, classify_and_filter
                articles = scrape_all()
                if articles:
                    filtered = classify_and_filter(articles)
                    out = "📰 *Berita Pasar Terbaru*\n━━━━━━━━━━━━━━━━━\n\n"
                    for a in filtered[:8]:
                        emoji_map = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}
                        emoji = emoji_map.get(a.get("sentiment", "neutral"), "⚪")
                        title = a["title"][:80] + "..." if len(a["title"]) > 80 else a["title"]
                        out += f"{emoji} {title}\n"
                        if a.get("category"):
                            out += f"  🏷 {a['category']}\n"
                        if a.get("source"):
                            out += f"  📍 {a['source']}\n"
                        out += "\n"
                    out += "━━━━━━━━━━━━━━━━━\n"
                    out += "💡 Ketik `/news BBCA` untuk berita spesifik saham"
                else:
                    out = "📰 *Berita Pasar*\n\nTidak ada berita terbaru saat ini.\n\n💡 Coba `/news BBCA` untuk berita spesifik saham."
                await msg.edit_text(out, parse_mode="Markdown")
            except Exception as e:
                await msg.edit_text(
                    f"❌ Gagal mengambil berita: {str(e)[:100]}\n\n"
                    "Coba `/news BBCA` untuk berita saham spesifik."
                )
            return

        # Symbol-specific news
        msg = await update.message.reply_text(f"📰 Mencari berita *{symbol}*...")
        try:
            from src.engine.news import NewsEngine
            engine = NewsEngine(max_days=30, max_articles=5)
            report = await engine.analyze(symbol)

            if report.articles:
                score_emoji = "🟢" if report.score >= 6 else ("🟡" if report.score >= 4 else "🔴")
                out = (
                    f"📰 *Berita {symbol}*\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"Sentiment: {score_emoji} *{report.score:.1f}/10* — {report.summary}\n"
                    f"Artikel: {report.total_articles} "
                    f"(🟢 {report.positive_count} | 🔴 {report.negative_count} | ⚪ {report.neutral_count})\n\n"
                )
                for a in report.articles[:5]:
                    emoji = "🟢" if a.sentiment == "positive" else ("🔴" if a.sentiment == "negative" else "⚪")
                    title = a.title[:70] + "..." if len(a.title) > 70 else a.title
                    out += f"{emoji} *{a.source}*: {title}\n\n"

                out += "━━━━━━━━━━━━━━━━━\n"
                out += f"💡 Analisa lengkap: `analisa {symbol}`"
            else:
                out = (
                    f"📰 *Berita {symbol}*\n\n"
                    f"Tidak ada berita terbaru untuk {symbol}.\n\n"
                    f"💡 Coba `/news` untuk berita pasar umum."
                )
            await msg.edit_text(out, parse_mode="Markdown")
        except Exception as e:
            await msg.edit_text(
                f"❌ Gagal mengambil berita {symbol}: {str(e)[:100]}\n\n"
                "Coba lagi nanti."
            )

    async def feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /feedback TLKM 5 or /fb TLKM bagus"""
        try:
            args = context.args
            if len(args) < 1:
                await update.message.reply_text(
                    "Format: `/feedback TLKM 5` atau `/fb BBCA bagus`\nRating 1-5.",
                    parse_mode="Markdown",
                )
                return

            symbol = args[0].upper()
            rating = None
            feedback_text = ""

            # Parse: "TLKM 4" or "TLKM bagus banget"
            if len(args) >= 2:
                try:
                    rating = int(args[1])
                    if rating < 1 or rating > 5:
                        rating = None
                    feedback_text = " ".join(args[2:]) if len(args) > 2 else ""
                except ValueError:
                    feedback_text = " ".join(args[1:])

            # Store in journal
            from src.models import AnalysisJournal
            from sqlalchemy import select
            from datetime import datetime
            db = await self._get_db()
            result = await db.execute(
                select(AnalysisJournal)
                .where(AnalysisJournal.symbol == symbol)
                .where(AnalysisJournal.user_rating.is_(None) | (AnalysisJournal.user_rating == 0))
                .order_by(AnalysisJournal.timestamp.desc())
                .limit(1)
            )
            entry = result.scalar_one_or_none()
            if entry:
                entry.user_rating = rating or 3
                entry.user_feedback_text = feedback_text or ""
                entry.feedback_at = datetime.utcnow()
                await db.commit()
                await update.message.reply_text(
                    f"✅ Makasih! Feedback untuk {symbol} tercatat.",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text(
                    f"Belum ada analisa {symbol} yang bisa di-feedback. Coba analisa dulu dengan `analisa {symbol}`",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.warning(f"Feedback error: {e}")
            await update.message.reply_text("❌ Gagal menyimpan feedback. Coba lagi.")

    # ── Upgrade (Payment) ──

    async def upgrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initiate payment for tier upgrade."""
        tier = context.args[0].lower() if context.args else ""
        valid_tiers = ["pro", "premium", "lifetime", "whitelabel"]

        if tier not in valid_tiers:
            keyboard = [
                [InlineKeyboardButton("💎 Pro Rp49rb/bln", callback_data="pay_pro")],
                [InlineKeyboardButton("👑 Premium Rp149rb/bln", callback_data="pay_premium")],
                [InlineKeyboardButton("🌟 Lifetime Rp1.999rb", callback_data="pay_lifetime")],
            ]
            await update.message.reply_text(
                "💳 *Upgrade Langganan*\n\n"
                "Pilih paket yang diinginkan:\n\n"
                "💎 *Pro* — Rp49.000/bulan\n"
                "👑 *Premium* — Rp149.000/bulan\n"
                "🌟 *Lifetime* — Rp1.999.000 (sekali bayar)\n\n"
                "Pembayaran via QRIS / Bank Transfer — otomatis aktif setelah bayar.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        await self._process_upgrade(update, tier)

    async def _process_upgrade(self, update, tier: str):
        """Create Tripay payment and send QR/payment link."""
        await update.message.reply_text("🔄 Membuat invoice pembayaran...")

        try:
            from src.services.payment import create_payment

            user = update.effective_user
            result = create_payment(
                user_id=user.id,
                username=user.username or user.first_name or "",
                tier=tier,
            )

            if result.get("success"):
                amount = result["amount"]
                pmt_url = result.get("payment_url", "")
                qr_url = result.get("qr_url", "")
                pay_code = result.get("pay_code", "")

                tier_label = {"pro": "Pro", "premium": "Premium", "lifetime": "Lifetime"}
                text = (
                    f"💳 *Pembayaran {tier_label.get(tier, tier)}*\n\n"
                    f"💰 Jumlah: *Rp{amount:,}*\n\n"
                )
                if qr_url:
                    text += f"📱 [Scan QRIS / Lihat QR]({qr_url})\n\n"
                if pay_code:
                    text += f"🔢 Kode Bayar: `{pay_code}`\n\n"
                if pmt_url:
                    text += f"🔗 [Buka Halaman Pembayaran]({pmt_url})\n\n"

                text += (
                    "✅ Setelah bayar, akun otomatis upgrade dalam 1-2 menit.\n"
                    "📋 Cek status: /myplans"
                )
                await update.message.reply_text(
                    text, parse_mode="Markdown", disable_web_page_preview=True,
                )
            else:
                error = result.get("error", "Gagal membuat pembayaran")
                await update.message.reply_text(
                    f"❌ Gagal: {error}\n\nCoba lagi atau hubungi admin.",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.warning(f"Upgrade error: {e}")
            await update.message.reply_text(
                "❌ Sistem pembayaran sedang sibuk. Coba lagi beberapa saat.",
                parse_mode="Markdown",
            )

    # ── Bandarmology ──

    async def bandarmology(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Premium-only bandarmology report."""
        try:
            from src.feed.rapidapi_idx import RapidAPIFeed
            from src.engine.bandarmology import BandarmologyEngine

            feed = RapidAPIFeed()
            broker = await feed.get_broker_flow_summary()
            all_brokers = await feed.get_top_brokers()
            broker['_all_brokers'] = all_brokers
            await feed.close()

            engine = BandarmologyEngine()
            report = engine.analyze(broker)

            out = f"🎰 *Bandarmology Report*\n"
            out += f"━━━━━━━━━━━━━━━━━━━━\n\n"
            out += f"{report.summary}\n\n"

            if report.foreign_accumulation_signals:
                out += "🟢 *Foreign Accumulation:*\n"
                for s in report.foreign_accumulation_signals[:5]:
                    out += f"  {s.broker_code} {s.broker_name}\n"
                    out += f"  Net +Rp{s.net_value:,.0f} ({s.strength})\n"

            if report.foreign_distribution_signals:
                out += "\n🔴 *Foreign Distribution:*\n"
                for s in report.foreign_distribution_signals[:5]:
                    out += f"  {s.broker_code} {s.broker_name}\n"
                    out += f"  Net -Rp{abs(s.net_value):,.0f} ({s.strength})\n"

            out += f"\n━━━━━━━━━━━━━━━━━━━━\n"
            out += f"💎 Upgrade ke Premium untuk alert bandar real-time: /pricing"

            await update.message.reply_text(out, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Bandarmology error: {e}")
            await update.message.reply_text(
                "🔒 *Bandarmology*\n\nData broker flow sedang tidak tersedia. Coba lagi nanti.",
                parse_mode="Markdown",
            )

    # ── Event Classifier (NEW — Premium) ──

    async def event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Classify corporate event from financial news text.
        Usage: /event PT Telkom umumkan dividen tunai Rp 14 triliun
        """
        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text(
                "📰 *Event Classifier*\n\n"
                "Klasifikasi berita korporat — 11 kategori event.\n\n"
                "*Contoh:*\n"
                "• `/event PT Telkom umumkan dividen tunai`\n"
                "• `/event Bank Mandiri buyback saham Rp 5T`\n"
                "• `/event GoTo resmi IPO di bursa`\n"
                "• `/event emiten properti akuisisi lahan Jakarta`\n\n"
                "💎 *Premium Feature* — 95.2% akurasi, 11 kelas event",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            "🔍 Menganalisa berita... (AI Event Classifier)",
        )

        try:
            from src.engine.event_classifier import classify_news, format_event_card

            result = classify_news(text)
            out = format_event_card(result, text)

            # Add CTA based on event type
            if result["signal"] > 0:
                out += "\n\n💡 Saham terkait potensi *BUY* — analisa dengan `analisa <kode>`"
            elif result["signal"] < 0:
                out += "\n\n⚠️ Saham terkait potensi *SELL* — verifikasi dengan `analisa <kode>`"

            out += "\n\n💎 Powered by FinBERT-ID + tuntun-news dataset (95.2% akurasi)"
            await update.message.reply_text(out, parse_mode="Markdown")

        except Exception as e:
            logger.warning(f"Event classifier error: {e}")
            await update.message.reply_text(
                "❌ Gagal klasifikasi berita. Coba lagi.\n\n"
                "💡 Pastikan teks berita berisi informasi korporat.",
                parse_mode="Markdown",
            )

    # ── Sector Forecast (NEW — Premium) ──

    async def sectorforecast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Premium sector volatility forecast — 11 sektor, 7 hari."""
        await update.message.reply_text(
            "📊 Menganalisa volatilitas 11 sektor... (mohon tunggu 30-60 detik)",
        )

        try:
            import os
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
            os.environ['PYTORCH_LIGHTNING_LOG_LEVEL'] = 'ERROR'
            import warnings
            warnings.filterwarnings('ignore')
            import logging
            logging.getLogger('pytorch_lightning').setLevel(logging.ERROR)
            logging.getLogger('lightning').setLevel(logging.ERROR)

            from src.engine.sector_forecast import predict_all_sectors, format_market_outlook

            results = predict_all_sectors()
            out = format_market_outlook(results)
            await update.message.reply_text(out, parse_mode="Markdown")

        except Exception as e:
            logger.warning(f"Sector forecast error: {e}")
            await update.message.reply_text(
                "❌ Gagal memproses forecast sektor. Coba lagi nanti.\n\n"
                "💡 Pastikan model HF tersedia di `data/models/sector_forecast/`",
                parse_mode="Markdown",
            )

    # ── IHSG Summary ──

    async def ihsg(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """IHSG market summary — 30 years of historical data."""
        await update.message.reply_text(
            "📊 Memuat data IHSG...", 
        )
        try:
            from src.feed.ihsg_data import get_ihsg_summary, format_ihsg_card
            summary = get_ihsg_summary()
            out = format_ihsg_card(summary)
            out += "\\n\\n💎 Premium: /sector untuk forecast 11 sektor"
            await update.message.reply_text(out, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"IHSG error: {e}")
            await update.message.reply_text(
                "❌ Gagal memuat data IHSG. Coba lagi nanti.",
                parse_mode="Markdown",
            )

    # ── Watchlist ──

    async def watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manage watchlist: /watchlist [add|remove|list] [symbol]"""
        try:
            from src.engine.watchlist import WatchlistEngine

            engine = WatchlistEngine()
            user_id = update.effective_user.id
            args = context.args or []

            if not args:
                digest = await engine.generate_digest(user_id)
                text = engine.format_digest(digest)
                await update.message.reply_text(text, parse_mode="Markdown")
                return

            action = args[0].lower()
            symbol = args[1].upper() if len(args) > 1 else ""

            if action == "add" and symbol:
                ok, msg = engine.add(user_id, symbol)
                await update.message.reply_text(msg, parse_mode="Markdown")
            elif action == "remove" and symbol:
                ok, msg = engine.remove(user_id, symbol)
                await update.message.reply_text(msg, parse_mode="Markdown")
            elif action == "list":
                entries = engine.list_stocks(user_id)
                if not entries:
                    await update.message.reply_text(
                        "📋 Watchlist kosong.\nTambah: `watchlist add BBCA`",
                        parse_mode="Markdown",
                    )
                else:
                    text = "📋 *Watchlist:*\n"
                    for e in entries:
                        text += f"  • {e.symbol}"
                        if e.last_price:
                            d = "🟢" if e.change_pct > 0 else ("🔴" if e.change_pct < 0 else "⚪")
                            text += f" Rp{e.last_price:,.0f} {d} {e.change_pct:+.1f}%"
                        text += "\n"
                    await update.message.reply_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    "📋 *Watchlist*\n\n"
                    "`/watchlist` — lihat digest\n"
                    "`/watchlist add BBCA` — tambah\n"
                    "`/watchlist remove BBCA` — hapus\n"
                    "`/watchlist list` — daftar saham",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.warning(f"Watchlist error: {e}")
            await update.message.reply_text("❌ Gagal mengakses watchlist. Coba lagi.")

    async def briefing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Daily AI Briefing — morning market snapshot."""
        msg = await update.message.reply_text("☀️ Menyusun briefing pagi... (30 detik)")
        try:
            from src.engine.briefing import build_briefing
            card = await build_briefing()
            await msg.edit_text(card, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Briefing error: {e}", exc_info=True)
            await msg.edit_text(
                f"❌ Gagal membuat briefing: {str(e)[:100]}\n\n"
                f"Coba cek koneksi atau ulangi nanti."
            )


def create_app() -> Application:
    """Create Telegram bot application instance."""
    from src.models import get_engine, create_tables

    # Ensure tables exist
    create_tables()

    handlers = BotHandlers()
    app = Application.builder().token(settings.bot_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help))
    app.add_handler(CommandHandler("pricing", handlers.pricing))
    app.add_handler(CommandHandler("myplans", handlers.myplans))
    app.add_handler(CommandHandler("myalerts", handlers.myalerts))
    app.add_handler(CommandHandler("performance", handlers.performance))
    app.add_handler(CommandHandler("feedback", handlers.feedback))
    app.add_handler(CommandHandler("fb", handlers.feedback))
    app.add_handler(CommandHandler("bandarmology", handlers.bandarmology))
    app.add_handler(CommandHandler("event", handlers.event))
    app.add_handler(CommandHandler("upgrade", handlers.upgrade))
    app.add_handler(CommandHandler("sector", handlers.sectorforecast))
    app.add_handler(CommandHandler("sectorforecast", handlers.sectorforecast))
    app.add_handler(CommandHandler("ihsg", handlers.ihsg))
    app.add_handler(CommandHandler("watchlist", handlers.watchlist))
    app.add_handler(CommandHandler("briefing", handlers.briefing))
    app.add_handler(CommandHandler("news", handlers.news))
    app.add_handler(CommandHandler("report", handlers.report))
    app.add_handler(CommandHandler("trending", handlers.trending))
    app.add_handler(MessageHandler(filters.TEXT, handlers.handle_message))
    app.add_handler(CallbackQueryHandler(handlers.button_callback, pattern="^sub_"))
    app.add_handler(CallbackQueryHandler(handlers.button_callback, pattern="^share_"))

    return app
