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
            "• `analisa TLKM` — analisa lengkap + chart\n"
            "• `screener akumulasi asing` — screening\n"
            "• `plan TLKM entry 4600 sl 4500 tp 4800` — trading plan\n"
            "• `alert TLKM >4600` — notifikasi harga\n\n"
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
            "• `analisa TLKM` — analisa teknikal + fundamental + flow\n"
            "• `cek BBCA` — jalan pintas\n"
            "• `TLKM` — cukup kirim kode saham\n\n"
            "*🔍 Screening*\n"
            "• `screener akumulasi asing` — saham diakumulasi asing\n"
            "• `screener volume spike` — saham dengan volume tinggi\n\n"
            "*📋 Trading Plan*\n"
            "• `plan TLKM entry 4600 sl 4500 tp 4800`\n\n"
            "*🔔 Alert Harga*\n"
            "• `alert TLKM >4600` — notifikasi harga menyentuh level\n\n"
            "*📈 Statistik*\n"
            "• `stats TLKM` — high, low, volume, nilai\n\n"
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
            "• Data delay 15 menit\n"
            "• 5 alert\n\n"
            "💎 *Pro — Rp49.000/bulan*\n"
            "• ✅ Unlimited screening\n"
            "• ✅ 50 alert\n"
            "• ✅ Real-time data\n"
            "• ✅ AI trade setup\n\n"
            "👑 *Premium — Rp149.000/bulan*\n"
            "• ✅ Semua Pro + 200 alert\n"
            "• ✅ Bandar View + komuntas eksklusif\n"
            "• ✅ Sesi mentor mingguan\n"
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
                    klines = await feed.get_klines(cmd.symbol, interval="1d", limit=90)
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

        out += f"\n{signal_emoji} *Score: {final_score}/10*  —  *{signal_text}*\n"
        if final_reasons:
            out += f"_{', '.join(final_reasons)}_\n"
        if ai_insight:
            out += f"\n🧠 *AI:*  {ai_insight}\n"

        out += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Ketik `analisa BBCA` atau `screener asing 3 hari`\n"
            f"💎 /pricing — real-time + 50 alert + analisa lebih dalam"
        )

        await update.message.reply_text(out, parse_mode="Markdown")

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
                "✅ Bandar View + flow institusi\n"
                "✅ Komunitas eksklusif & mentor mingguan\n"
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
    app.add_handler(MessageHandler(filters.TEXT, handlers.handle_message))
    app.add_handler(CallbackQueryHandler(handlers.button_callback, pattern="^sub_"))

    return app
