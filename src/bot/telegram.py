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
from src.bot.tier_gate import check_tier, get_tier_badge, get_tier_limits

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

    async def _check_tier(self, update: Update, command: str) -> bool:
        """Check tier access. Returns True if allowed, sends message and returns False if not."""
        user_id = update.effective_user.id
        has_access, tier, msg = check_tier(user_id, command)
        if not has_access:
            logger.info(f"Tier gate: user={user_id} tier={tier} blocked={command}")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return False
        return True

    # ── Start / Help ──

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_tier(update, "start"): return
        
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "Trader"
        from src.bot.tier_gate import get_user_tier_sync, get_tier_badge
        tier = get_user_tier_sync(user_id)
        badge = get_tier_badge(tier)
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        if tier == "admin":
            text = (
                f"⚡ *Admin Panel — Vilona Saham*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 *{user_name}*  {badge}\n"
                f"🔓 Akses *FULL* — 34 commands\n\n"
                f"📊 *Quick Actions:*\n"
                f"• `analisa BBCA` — analisa lengkap + chart\n"
                f"• `screener momentum` — cari saham momentum\n"
                f"• `plan TLKM` — auto trading plan\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📖 /help — semua command\n"
                f"💳 /pricing — info langganan"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            # Dynamic stock count
            try:
                from src.engine.idx_universe import IDX_UNIVERSE
                stock_count = len(IDX_UNIVERSE)
            except:
                stock_count = 693
            
            text = (
                f"🚀 *Selamat Datang, {user_name}!*\n\n"
                f"*Vilona Saham* — AI Copilot trading saham IDX.\n"
                f"Satu bot: chart TradingView + analisa AI + data bandar + trading plan otomatis.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 *{stock_count} saham IDX* di-scan real-time\n"
                f"🧠 *AI analisa* dalam Bahasa Indonesia\n"
                f"📈 *Chart premium* + indikator teknikal\n"
                f"🏦 *Bandarmology* — deteksi akumulasi institusi\n\n"
                f"👤 Status: *{tier.title()}* {badge}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 *Coba sekarang:*\n"
                f"• `analisa BBCA` — analisa lengkap\n"
                f"• `screener momentum` — cari saham momentum\n"
                f"• `plan TLKM` — auto trading plan\n\n"
                f"📖 /help — semua command\n"
                f"💳 /pricing — langganan"
            )
            
            keyboard = [
                [InlineKeyboardButton("🎓 Mulai Tour (5 menit)", callback_data="onboarding:start")],
                [InlineKeyboardButton("💳 Lihat Harga", callback_data="onboarding:pricing")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text, parse_mode="Markdown", reply_markup=reply_markup
            )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_tier(update, "help"): return
        
        user_id = update.effective_user.id
        from src.bot.tier_gate import get_user_tier_sync, get_tier_badge
        tier = get_user_tier_sync(user_id)
        badge = get_tier_badge(tier)
        
        # Core commands (all tiers)
        core = (
            "📖 *Vilona Saham — Semua Command*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Status: *{tier.title()}* {badge}\n\n"
            "💡 *Ketik natural — nggak perlu hafal perintah.*\n"
            "Contoh: `analisa BBCA`, `screener momentum`, `plan TLKM`\n\n"
        )
        
        # Free commands
        free = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🆓 *Gratis:*\n"
            "• `analisa BBCA` — analisa + chart + AI\n"
            "• `stats BBCA` — data pasar\n"
            "• `ihsg` — data IHSG real-time\n"
            "• `news` — berita pasar\n"
            "• `trending` — saham trending\n\n"
        )
        
        # Pro commands (gated)
        pro = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 *Pro — Rp49k/bulan:*\n"
            "• `screener momentum` — momentum kuat\n"
            "• `screener reversal` — siap balik arah\n"
            "• `screener breakout` — breakout detector\n"
            "• `screener smart money` — jejak akumulasi\n"
            "• `plan TLKM` — auto trading plan\n"
            "• `alert TLKM >4600` — notifikasi harga\n"
            "• `portfolio` — tracking posisi\n"
            "• `premarket` — kondisi global\n"
            "• `briefing` — ringkasan pasar\n\n"
        )
        
        # Premium commands (gated)
        premium = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👑 *Premium — Rp149k/bulan:*\n"
            "• `bandarmology` — deteksi bandar + asing\n"
            "• `event` — klasifikasi berita korporat\n"
            "• `report` — laporan mingguan\n"
            "• `jejak` — profit trail + performa\n"
            "• `leaderboard` — top trader\n"
            "• `points` — poin & rank\n\n"
        )
        
        # Footer
        footer = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💳 *Langganan* — /pricing\n"
            "📊 *Scanning 704 saham IDX real-time*"
        )
        
        # Build based on tier
        text = core
        
        if tier == "admin":
            # Admin sees all
            text += free + pro + premium + footer
        elif tier == "premium":
            text += free + pro + premium + footer
        elif tier == "pro":
            text += free + pro + "\n👑 *Upgrade Premium untuk 9 command lagi!*\n" + footer
        else:
            text += free + "\n💎 *Upgrade Pro untuk 16 command lagi!*\n" + footer
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def panduan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Panduan lengkap Vilona Saham — scroll paginated untuk user Indonesia."""
        if not await self._check_tier(update, "panduan"): return

        user_id = update.effective_user.id
        from src.bot.tier_gate import get_user_tier_sync, get_tier_badge
        tier = get_user_tier_sync(user_id)
        badge = get_tier_badge(tier)

        # Simpan tier di context untuk dipake di callback
        context.user_data["panduan_tier"] = tier
        context.user_data["panduan_badge"] = badge
        context.user_data["panduan_page"] = 1

        text, keyboard = self._panduan_page(1, tier, badge)
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    def _panduan_page(self, page: int, tier: str, badge: str):
        """Render panduan page + inline keyboard."""
        from telegram import InlineKeyboardButton

        if page == 1:
            text = (
                f"📚 *PANDUAN LENGKAP VILONA SAHAM* 🇮🇩  |  1/5\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Tier kamu:* {tier.title()} {badge}\n\n"
                f"*Apa itu Vilona Saham?*\n"
                f"Bot AI analisa saham IDX — pakai AI "
                f"(DeepSeek • Groq • OmniRoute) + data *real-time BEI*.\n\n"
                f"Tinggal ketik natural, langsung dapet:\n"
                f"• 📈 Chart + analisa teknikal\n"
                f"• 🧠 Narasi AI bahasa Indonesia\n"
                f"• 🏦 Arus dana asing & bandar\n"
                f"• 🎯 Auto trading plan (Entry/SL/TP)\n"
                f"• ⭐ Confidence Score 1-10\n\n"
                f"🚀 *MULAI CEPAT — 3 Langkah*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"*1️⃣ Analisa Saham*\n"
                f"Ketik: `analisa BBCA`\n"
                f"→ Dapet chart + narasi AI + score + auto plan.\n\n"
                f"*2️⃣ Cari Saham Potensial*\n"
                f"Ketik: `screener momentum` (Pro/Premium)\n"
                f"→ Scan 693 saham dalam 0.1 detik — top picks.\n\n"
                f"*3️⃣ Pasang Alert*\n"
                f"Ketik: `alert TLKM >2600` (Pro/Premium)\n"
                f"→ Bot auto DM pas harga kena target.\n"
            )
            nav = [None, None, "2", "Selanjutnya →"]

        elif page == 2:
            text = (
                f"📋 *DAFTAR COMMAND* — GRATIS  |  2/5\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 `analisa BBCA`\n"
                f"  Chart + AI narasi + data bandar + score 1-10.\n"
                f"  AI kasih *BUY/WATCH/PASS* + alasan.\n"
                f"  _Contoh: `analisa TLKM`, `analisa GOTO`_\n\n"
                f"📈 `stats BBCA`\n"
                f"  Harga, volume, nilai transaksi.\n"
                f"  _Contoh: `stats BRIS`_\n\n"
                f"🏛️ `ihsg`\n"
                f"  Data IHSG real-time.\n\n"
                f"📰 `news`\n"
                f"  Berita pasar Indonesia (CNBC, Kontan).\n"
                f"  _Contoh: `news BBCA`_\n\n"
                f"🔥 `trending`\n"
                f"  Saham paling trending saat ini.\n\n"
                f"💳 `pricing`\n"
                f"  Paket langganan + harga.\n\n"
                f"📖 `help` / `panduan`\n"
                f"  Daftar command + tutorial.\n"
            )
            nav = ["1", "← Kembali", "3", "Selanjutnya →"]

        elif page == 3:
            text = (
                f"💎 *PRO — Rp49rb/bulan* ← PALING DIMINATI  |  3/5\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔍 `screener momentum` — saham momentum kencang\n"
                f"🔄 `screener reversal` — siap balik arah\n"
                f"💥 `screener breakout` — tembus level kunci\n"
                f"🐋 `screener smart money` — jejak akumulasi bandar\n\n"
                f"📋 `plan TLKM entry 2500 sl 2400 tp 2700`\n"
                f"  Auto plan + bot pantau SL/TP — kirim notif kalau kena.\n\n"
                f"🔔 `alert TLKM >2600`\n"
                f"  Alert harga real-time, maks 50 alert.\n"
                f"  _Contoh: `alert BBCA >6000`_\n\n"
                f"💼 `portfolio`\n"
                f"  Tracking posisi + P/L.\n\n"
                f"🌅 `premarket`\n"
                f"  Kondisi pre-market Wall Street + IHSG.\n\n"
                f"📊 `briefing`\n"
                f"  Ringkasan pasar harian.\n"
            )
            if tier in ("pro", "premium", "admin"):
                nav = ["2", "← Kembali", "4", "Selanjutnya →"]
            else:
                text += f"\n💳 Upgrade: /pricing"
                nav = ["2", "← Kembali", "4", "Selanjutnya →"]

        elif page == 4:
            text = (
                f"👑 *PREMIUM — Rp149rb/bulan*  |  4/5\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🎰 `bandarmology`\n"
                f"  Deteksi aktivitas bandar — broker akumulasi / distribusi.\n"
                f"  Skor: Strong Buy → Buy → Hold → Sell → Strong Sell.\n\n"
                f"📰 `event`\n"
                f"  Klasifikasi berita: RUPS, dividen, right issue, IPO.\n"
                f"  _Contoh: `event BBCA`_\n\n"
                f"📝 `report`\n"
                f"  Laporan performa mingguan — win rate, P/L.\n\n"
                f"👣 `jejak`\n"
                f"  Profit trail — history per saham.\n\n"
                f"🏆 `leaderboard`\n"
                f"  Top trader minggu ini.\n\n"
                f"⭐ `points`\n"
                f"  XP & rank dari aktivitas trading.\n"
            )
            if tier in ("premium", "admin"):
                nav = ["3", "← Kembali", "5", "Selanjutnya →"]
            else:
                text += f"\n💳 Upgrade: /pricing"
                nav = ["3", "← Kembali", "5", "Selanjutnya →"]

        else:  # page == 5
            text = (
                f"🎯 *TIPS + FAQ*  |  5/5\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🎯 *TIPS TRADER IDX*\n"
                f"1. Pagi (08:00-09:30) analisa LQ45: BBCA, BBRI, TLKM, ASII\n"
                f"2. Screener pagi: momentum + breakout. Siang: reversal + smart money\n"
                f"3. SL maks 5-8%. Risk/Reward minimal 1:2\n"
                f"4. Sesi 1 (09:00-12:00) entry, Sesi 2 (13:30-15:00) manajemen\n"
                f"5. Pantau asing: net buy >Rp50M dalam 3 hari = sinyal kuat\n\n"
                f"💡 *FAQ*\n"
                f"*Q: Data real-time?*\n"
                f"  Pro/Premium: real-time BEI. Free: delay 15 menit.\n\n"
                f"*Q: AI akurat?*\n"
                f"  AI pakai teknikal + fundamental + broker flow.\n"
                f"  Score 10 = sinyal kuat. Score <6 = hati-hati.\n\n"
                f"*Q: Bisa di HP?*\n"
                f"  Ya! Telegram Android/iPhone/Web — gak perlu install apa-apa.\n\n"
                f"*Q: Support?*\n"
                f"  DM @alwayscuanbos — respon <1 jam (09:00-17:00 WIB).\n\n"
                f"🔗 *LINK*\n"
                f"📊 Dashboard: https://botidx.aitradepulse.com/dashboard\n"
                f"🤖 Bot: @vilonidxbot\n"
            )
            nav = ["4", "← Kembali", None, None]

        # Build inline keyboard
        row = []
        if nav[0]:
            row.append(InlineKeyboardButton(f"← {nav[1]}", callback_data=f"panduan:{nav[0]}"))
        if nav[2]:
            row.append(InlineKeyboardButton(f"{nav[3]} →", callback_data=f"panduan:{nav[2]}"))
        keyboard = [row] if row else []

        return text, keyboard

    async def analisa_direct(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Direct handler for /analisa command."""
        if not await self._check_tier(update, "analisa"): return
        # Free tier: limit 5 analyses/day
        user_id = update.effective_user.id
        from src.bot.tier_gate import get_user_tier_sync, get_tier_limits
        tier = get_user_tier_sync(user_id)
        limits = get_tier_limits(tier)
        
        # Check daily limit (TODO: track daily count in DB)
        # For now, Pro+ users get unlimited
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "📝 *Cara pakai:* /analisa BBCA\n\n"
                "Ketik nama saham setelah command.",
                parse_mode="Markdown"
            )
            return
        symbol = args[0].upper()
        await self.analyze(update, context, symbol)

    async def stats_direct(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Direct handler for /stats command."""
        if not await self._check_tier(update, "stats"): return
        args = context.args
        if not args:
            await update.message.reply_text(
                "📝 *Cara pakai:* /stats BBCA\n\n"
                "Ketik nama saham setelah command.",
                parse_mode="Markdown"
            )
            return
        symbol = args[0].upper()
        # Route to analyze with stats focus
        await self.analyze(update, context, symbol)

    async def pricing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_tier(update, "pricing"): return
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
            "💰 *Vilona Saham — Langganan*\n\n"
            "_Dari bingung liat chart → langsung tau entry, SL, TP. 10 detik._\n\n"
            "━━━━━━━━━━━━━━━━━\n"
            "🆓 *Gratis — Rp0*\n"
            "• 5 analisa / hari\n"
            "• 3 saham watchlist\n"
            "• Data delay 15 menit\n"
            "• 5 alert\n"
            "• AI basic\n\n"
            "💎 *Pro — Rp49rb/bulan* ← PALING DIMINATI\n"
            "━━━━━━━━━━━━━━━━━\n"
            "✅ Unlimited analisa + screener 693 saham\n"
            "✅ Trading plan auto (Entry/SL/TP/R:R)\n"
            "✅ 50 alert real-time\n"
            "✅ Data real-time\n"
            "✅ Portfolio tracking\n"
            "✅ Watchlist 10 saham\n"
            "✅ AI trade setup + Confidence Score\n\n"
            "👑 *Premium — Rp149rb/bulan*\n"
            "━━━━━━━━━━━━━━━━━\n"
            "✅ SEMUA fitur Pro +\n"
            "✅ Deteksi Bandar + Arus Asing\n"
            "✅ Market Sentiment (Fear & Greed)\n"
            "✅ Forecast 11 Sektor IDX (7 hari)\n"
            "✅ Event Classifier (RUPS, dividen, rights)\n"
            "✅ Laporan Mingguan (otomatis Senin pagi)\n"
            "✅ Jejak Cuan + Distribusi Performa\n"
            "✅ 200 alert\n"
            "✅ Notifikasi SL/TP auto\n"
            "✅ Priority AI response\n\n"
            "🌟 *Lifetime — Rp1.999rb*\n"
            "• Akses Premium selamanya\n"
            "• ⚠️ Sisa 998 dari 1000 seat\n\n"
            "🏢 *White-label — Rp5jt + Rp500rb/bln*\n"
            "• Branding sendiri + panel admin\n"
            "• Jual ke komunitas kamu\n\n"
            "━━━━━━━━━━━━━━━━━\n"
            "🎁 *Baru?* Coba Premium GRATIS 7 hari — klik di bawah\n"
            "🔒 Garansi 7 hari: nggak cocok = refund penuh\n"
            "💡 Trader lain udah pake. Giliran lo."
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
            price = float(quote_raw.get("price") or 0)
            change = float(quote_raw.get("change_pct") or 0)
        elif quote_raw and hasattr(quote_raw, "price"):
            price = float(quote_raw.price or 0)
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
            closes = [float(k["close"]) for k in klines if k.get("close") is not None]
            highs = [float(k["high"]) for k in klines if k.get("high") is not None]
            lows = [float(k["low"]) for k in klines if k.get("low") is not None]
            volumes = [int(k["volume"]) for k in klines if k.get("volume") is not None]

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
            await update.message.reply_text(f"❌ Data {symbol} tidak ditemukan.")
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

        # Stochastic
        try:
            from src.engine.indicator_defs import stochastic
            stoch = stochastic(
                [float(k.get("high", 0) or 0) for k in klines_raw if isinstance(k, dict)],
                [float(k.get("low", 0) or 0) for k in klines_raw if isinstance(k, dict)],
                [float(k.get("close", 0) or 0) for k in klines_raw if isinstance(k, dict)],
            )
            if stoch:
                sto_emoji = "🟢" if stoch.signal == "oversold" else ("🔴" if stoch.signal == "overbought" else "➖")
                text += f"  {sto_emoji} STOCH: %K {stoch.k:.0f} %D {stoch.d:.0f} ({stoch.signal})\n"
        except Exception:
            pass

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
        text += "\n🏦 *Arus Asing:*\n"
        if flow_data and flow_data.net_buy != 0:
            dir_emoji = "🟢" if flow_data.is_net_buy() else "🔴"
            dir_text = "Net Buy" if flow_data.is_net_buy() else "Net Sell"
            text += f"  {dir_emoji} {dir_text}: Rp{abs(flow_data.net_buy):,.0f}\n"
            text += f"  Beli: Rp{flow_data.foreign_buy:,.0f} | Jual: Rp{flow_data.foreign_sell:,.0f}\n"
            if flow_data.streak_days > 0:
                text += f"  Streak: {flow_data.streak_days} hari\n"
        elif rapidapi_broker:
            fnb = rapidapi_broker.get("foreign_net_buy", 0)
            if fnb != 0:
                dir_emoji = "🟢" if fnb > 0 else "🔴"
                dir_text = "Net Buy" if fnb > 0 else "Net Sell"
                text += f"  {dir_emoji} {dir_text} Asing: Rp{abs(fnb):,.0f}\n"
                text += f"  Beli: Rp{rapidapi_broker.get('foreign_buy',0):,.0f} | Jual: Rp{rapidapi_broker.get('foreign_sell',0):,.0f}\n"
                text += f"  Porsi Asing: {rapidapi_broker.get('foreign_domestic_ratio',0)*100:.1f}%\n"
            else:
                text += "  Asing net flat hari ini\n"
        else:
            text += "  Asing lagi santai hari ini\n"

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
            text += f"\n🧠 *Analisa AI:*\n  {ai_insight}\n"

        # ─── SMC Structure + Auto Trading Plan ──────────────────
        smc_trend = ""
        try:
            from src.engine.smc_structure import SMCStructureEngine
            from src.engine.trading_plan import TradingPlanEngine

            # Build OHLC from klines for SMC + plan
            if klines_raw and len(klines_raw) > 20:
                ohlc = []
                for k in klines_raw:
                    if isinstance(k, dict):
                        ohlc.append(k)
                    elif hasattr(k, "close"):
                        ohlc.append({
                            "open": float(k.open or 0), "high": float(k.high or 0),
                            "low": float(k.low or 0), "close": float(k.close or 0),
                            "volume": float(getattr(k, "volume", 0) or 0),
                            "timestamp": str(getattr(k, "timestamp", "")),
                        })

                if ohlc and len(ohlc) >= 20:
                    # SMC structure
                    smc = SMCStructureEngine().analyze(ohlc, symbol)
                    smc_trend = smc.trend

                    # Volume ratio
                    vols = [float(c.get("volume", 0) or 0) for c in ohlc[-20:]]
                    vol_avg = sum(vols) / len(vols) if vols else 1
                    recent_vol = sum(vols[-5:]) / 5 if len(vols) >= 5 else vol_avg
                    vol_ratio = recent_vol / vol_avg if vol_avg > 0 else 1.0

                    # Accumulation: from bandarmology if available
                    acc_score = 50
                    if rapidapi_broker:
                        fnb = rapidapi_broker.get("foreign_net_buy", 0)
                        fbo = rapidapi_broker.get("foreign_domestic_ratio", 0) * 100
                        if fnb > 200_000_000_000:
                            acc_score = min(100, 60 + int(fbo))
                        elif fnb > 0:
                            acc_score = 50 + int(min(fbo, 30))
                        elif fnb < -200_000_000_000:
                            acc_score = max(0, 40 - int(fbo))

                    # Generate trading plan
                    plan = TradingPlanEngine().generate(
                        symbol, price, ohlc,
                        smc_trend=smc.trend,
                        accumulation_score=acc_score,
                        volume_ratio=vol_ratio,
                    )

                    # Structure tag
                    if smc.trend == "BULLISH":
                        bos_tag = "🟢 BOS" if smc.recent_bos else "🟢 BULLISH"
                    elif smc.trend == "BEARISH":
                        bos_tag = "🔴 CHoCH" if smc.recent_choch else "🔴 BEARISH"
                    else:
                        bos_tag = "⚪ NEUTRAL"

                    grade_emoji = {"A": "🏆", "B": "✅", "C": "⚠️", "D": "❌"}

                    text += (
                        f"\n🎯 *Trading Plan*\n"
                        f"  📐 Structure: {bos_tag}  |  "
                    )
                    if smc.liquidity_sweeps:
                        sweep = smc.liquidity_sweeps[-1]
                        sweep_icon = "🐻" if sweep.direction == "BEAR_TRAP" else "🐂"
                        text += f"{sweep_icon} {sweep.direction.replace('_',' ')}\n"
                    else:
                        text += "\n"

                    text += (
                        f"  🎯 Signal: *{plan.signal}*  |  "
                        f"⭐ *{plan.confidence}/20*{grade_emoji.get(plan.grade, '')} Grade {plan.grade}\n\n"
                        f"  📍 Entry: *Rp{plan.entry_min:,.0f} – Rp{plan.entry_max:,.0f}*\n"
                        f"  🛑 SL: *Rp{plan.stop_loss:,.0f}* ({plan.sl_pct}%)\n"
                        f"  🎯 TP1: *Rp{plan.tp1:,.0f}* (+{plan.tp1_pct}%)\n"
                        f"  🚀 TP2: *Rp{plan.tp2:,.0f}* (+{plan.tp2_pct}%)\n"
                        f"  ⚖️ RR: *1:{plan.rr_ratio}*\n"
                    )
                    if plan.vwap > 0:
                        text += f"  📊 VWAP: Rp{plan.vwap:,.0f} ({plan.vwap_pct:+.1f}%)\\n"

                    # BOS/BOW tag for scoring
                    text += f"\n  🏷️ *{', '.join(plan.reasoning[:2])}*\n"

        except Exception as e:
            logger.warning(f"SMC/TradingPlan failed: {e}")

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
            from src.models import AnalysisJournal
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
                    if smc_trend:
                        tag = {"BULLISH": "🟢 BULLISH", "BEARISH": "🔴 BEARISH", "NEUTRAL": "⚪ NEUTRAL"}
                        caption += f"  |  {tag.get(smc_trend, '')}"
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
                f"🔴 Resistance: Rp{zones['resistance']:,.0f}    🟢 Support: Rp{zones['support']:,.0f}\n"
                f"🎯 Entry Ideal: Rp{zones['entry_zone_low']:,.0f} - Rp{zones['entry_zone_high']:,.0f}\n"
                f"\n📊 *Indikator*\n"
                f"RSI: {rsi_str}  │  MACD: {macd_emoji} {macd_trend}\n"
                f"SMA20: {sma20:,.0f}  │  SMA50: {sma50:,.0f}\n"
                f"Volume: {vol_status}{bb_str}\n"
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
                out += f"  🟢 Asing lagi akumulasi: Rp{fnb:,.0f} ({fbr:.1f}% foreign)\n"
            elif fnb < -200_000_000_000:
                out += f"  🔴 Asing distribusi: Rp{abs(fnb):,.0f}\n"
            else:
                out += f"  ⚪ Asing netral: Rp{fnb:,.0f}\n"

            # Top broker
            top_brokers = rapidapi_broker.get("top_brokers", [])
            foreign_brokers = [b for b in top_brokers if b.get("group") == "BROKER_GROUP_FOREIGN"]
            if foreign_brokers:
                top = foreign_brokers[0]
                out += f"  🔝 {top['code']} {top['name']}: Net Rp{float(top['net_value']):,.0f}\n"

        out += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Coba: `screener momentum` atau `plan TLKM`\n"
            f"💎 /pricing — real-time data + 50 alert"
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

        # ─── Gamification: award point ──────────────────────
        try:
            from src.engine.gamification import award
            award(update.effective_user.id, "analisa", update.effective_user.username or "")
        except Exception:
            pass

    # ── My Plans ──

    async def myplans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_tier(update, "myplans"): return
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
                    "💡 Nanti saya kabarin kalau kena SL/TP."
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
        if not await self._check_tier(update, "myalerts"): return
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
        if not await self._check_tier(update, "performance"): return
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
                f"Total: {perf['total_trades']} transaksi\n"
                f"Menang: {perf['wins']} | Kalah: {perf['losses']}\n"
                f"{wr_color} Win Rate: {perf['win_rate']}%\n"
                f"{pnl_emoji} Realisasi: Rp{abs(total_pnl):,.0f}\n"
                f"Plan aktif: {perf['active']}\n\n"
                f"📋 Lihat plan: /myplans\n"
                f"💡 Analisa saham: `analisa BBCA`"
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
        lower = text.lower()

        # ── Quick-route panduan ──
        if lower in ("panduan", "/panduan", "panduan bot", "guide", "cara pakai"):
            await self.panduan(update, context)
            return

        # ── Tier check for NLP-routed commands ──
        if not await self._check_tier(update, "handle_message"): return
        
        cmd = self.nlp.parse(text)

        if cmd.intent == Intent.ANALYZE:
            try:
                await self.analyze(update, context, cmd.symbol)
            except Exception as e:
                logger.error(f"Analyze failed: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Gagal menganalisa: {str(e)[:100]}"
                )
        # ── Category Screeners (NLP routed) ──
        elif cmd.intent in (Intent.SCREEN_MOMENTUM, Intent.SCREEN_REVERSAL,
                             Intent.SCREEN_BREAKOUT, Intent.SCREEN_SMARTMONEY):
            cat_map = {
                Intent.SCREEN_MOMENTUM: "momentum",
                Intent.SCREEN_REVERSAL: "reversal",
                Intent.SCREEN_BREAKOUT: "breakout",
                Intent.SCREEN_SMARTMONEY: "smartmoney",
            }
            await self._run_category_screener(update, cat_map[cmd.intent])
            return
        elif cmd.intent == Intent.SCREEN:
            rules = cmd.params.get('rules', ['technical', 'fundamental', 'foreign_flow'])
            try:
                from src.engine.idx_encyclopedia import all_stocks
                symbols = list(all_stocks().keys())
            except Exception:
                symbols = ['BBCA', 'BBRI', 'BMRI', 'BBNI', 'TLKM', 'ASII', 'ADRO', 'UNVR', 
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
                        "Nggak ada saham yang lolos kriteria saat ini.\n\n"
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
                        source_message_id=getattr(update.message, 'message_id', None),
                        source_chat_id=update.effective_chat.id,
                    )
                    if plan:
                        text = (
                            f"📋 *Plan Tersimpan* — {cmd.symbol}\n"
                            f"Entry: Rp{plan.entry_price:,.0f}\n"
                            f"SL: Rp{plan.stop_loss:,.0f}\n"
                            f"TP: Rp{plan.take_profit:,.0f} "
                            f"{'✅' if plan.risk_reward >= 2 else '🟡' if plan.risk_reward >= 1.5 else '⚠️'} R:R {plan.risk_reward}x\n\n"
                            "Auto-report aktif — saya kirim notifikasi kalau kena SL/TP.\n"
                            "📊 Cek performa: /performance"
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
                        # ─── Gamification ───────────────
                        try:
                            from src.engine.gamification import award
                            award(update.effective_user.id, "plan_trade", update.effective_user.username or "")
                        except Exception:
                            pass
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
                            f"Pantau: {alert.symbol} {alert.condition} Rp{alert.value:,.0f}\n"
                            f"Alert aktif: {active}/{limit}\n\n"
                            f"Nanti saya kabarin kalau harga nyentuh level ini.\n"
                            f"📋 Cek semua alert: /myalerts"
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
                    f"Tertinggi: Rp{quote.high:,.0f}\n"
                    f"Terendah: Rp{quote.low:,.0f}\n"
                    f"Volume: {quote.volume:,}\n"
                    f"Nilai: Rp{quote.value:,.0f}\n\n"
                    f"💡 Analisa lengkap: `analisa {cmd.symbol}`"
                )
            else:
                text = (
                    f"❌ Data {cmd.symbol} tidak tersedia.\n\n"
                    "Coba: `stats BBCA` atau `analisa TLKM`"
                )
            await update.message.reply_text(text, parse_mode="Markdown")
        elif cmd.intent == Intent.HELP:
            await self.help(update, context)
        elif cmd.intent == Intent.PRICING:
            await self.pricing(update, context)
        else:
            await update.message.reply_text(
                "🤔 *Perintah nggak dikenal*\n\n"
                "Coba salah satu ini:\n"
                "• `analisa TLKM` — analisa saham\n"
                "• `screener momentum` — cari saham panas\n"
                "• `plan TLKM entry 4600 sl 4500 tp 4800` — trading plan\n"
                "• /help — semua perintah\n\n"
                "Atau kirim kode saham aja kayak `TLKM`",
                parse_mode="Markdown",
            )

    async def _onboarding_step(self, update: Update, context: ContextTypes.DEFAULT_TYPE, step: int) -> None:
        """Interactive onboarding tour — guided walkthrough of 4 core features."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        query = update.callback_query
        user_tier_query = query.message.chat.id
        
        if step == 1:
            text = (
                f"🎓 *Tour Vilona Saham — 1/5*\\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                f"📊 *Analisa Saham*\\n\\n"
                f"Ketik `analisa BBCA` untuk dapet:\\n"
                f"• 📈 Chart TradingView (dark theme)\\n"
                f"• 🧠 AI narasi — bahasa Indonesia natural\\n"
                f"• 🏦 Data bandar & asing\\n"
                f"• 📋 Auto trading plan (entry, SL, TP)\\n"
                f"• 📊 Score trading 1-10\\n\\n"
                f"💡 *10 detik — dari bingung liat chart jadi tau entry.*"
            )
            keyboard = [
                [InlineKeyboardButton("📊 Coba Analisa BBCA →", callback_data="analisa:BBCA")],
                [InlineKeyboardButton("Selanjutnya →", callback_data="onboarding:step1")],
            ]
            
        elif step == 2:
            text = (
                f"🔍 *Tour Vilona Saham — 2/5*\\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                f"🔍 *Screener Saham*\\n\\n"
                f"Scan *693 saham IDX* otomatis dalam 5 detik.\\n"
                f"4 kategori:\\n"
                f"• 🔥 *Momentum* — saham dengan tenaga naik\\n"
                f"• 🔄 *Reversal* — siap berbalik arah\\n"
                f"• 💥 *Breakout* — tembus level kunci\\n"
                f"• 🐋 *Smart Money* — jejak akumulasi bandar\\n\\n"
                f"💡 *Gak perlu hafal 300 command — cukup ketik kategori.*"
            )
            keyboard = [
                [InlineKeyboardButton("🔍 Cari Saham Momentum →", callback_data="screener:momentum")],
                [InlineKeyboardButton("← Kembali", callback_data="onboarding:start"), InlineKeyboardButton("Selanjutnya →", callback_data="onboarding:step2")],
            ]
            
        elif step == 3:
            text = (
                f"📋 *Tour Vilona Saham — 3/5*\\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                f"📋 *Auto Trading Plan*\\n\\n"
                f"AI generate trading plan otomatis:\\n"
                f"• 🎯 Entry zone (support/resistance)\\n"
                f"• 🛑 Stop Loss (max 8% risk)\\n"
                f"• 🏆 TP1 & TP2 (risk/reward)\\n"
                f"• ⭐ Risk/Reward ratio\\n"
                f"• 📊 Confidence score + Grade (A/B/C/D)\\n\\n"
                f"💡 *Plan terpicu SL/TP? Bot auto notifikasi.*"
            )
            keyboard = [
                [InlineKeyboardButton("📋 Lihat Plan TLKM →", callback_data="plan:TLKM")],
                [InlineKeyboardButton("← Kembali", callback_data="onboarding:step1"), InlineKeyboardButton("Selanjutnya →", callback_data="onboarding:step3")],
            ]
            
        elif step == 4:
            text = (
                f"🔔 *Tour Vilona Saham — 4/5*\\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                f"🔔 *Price Alert + Notifikasi*\\n\\n"
                f"Pasang alert harga — bot kirim notifikasi\\n"
                f"otomatis ke Telegram pas harga kena.\\n\\n"
                f"• `alert BBCA >5500` — naik ke 5500\\n"
                f"• `alert TLKM <2500` — turun ke 2500\\n"
                f"• Auto-pantau SL/TP dari trading plan\\n"
                f"• Notifikasi real-time via DM\\n\\n"
                f"💡 *Gak perlu manteng chart seharian.*"
            )
            keyboard = [
                [InlineKeyboardButton("🔔 Pasang Alert BBCA →", callback_data="alert_demo")],
                [InlineKeyboardButton("← Kembali", callback_data="onboarding:step2"), InlineKeyboardButton("Selesai →", callback_data="onboarding:step4")],
            ]
            
        else:  # step == 5 (conclusion)
            text = (
                f"🏆 *Tour Vilona Saham — 5/5*\\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                f"🎉 *Kamu udah siap!*\\n\\n"
                f"Sekarang kamu bisa:\\n"
                f"✅ Analisa saham pakai AI\\n"
                f"✅ Cari saham momentum/reversal\\n"
                f"✅ Buat trading plan otomatis\\n"
                f"✅ Pasang alert real-time\\n\\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"📌 *Mulai sekarang:*\\n"
                f"• `analisa BBCA` — analisa lengkap\\n"
                f"• `screener momentum` — cari saham panas\\n\\n"
                f"📖 /help — semua command\\n"
                f"💳 /pricing — upgrade ke Pro/Premium"
            )
            keyboard = [
                [InlineKeyboardButton("📊 Analisa BBCA", callback_data="analisa:BBCA")],
                [InlineKeyboardButton("🔍 Cari Momentum", callback_data="screener:momentum")],
                [InlineKeyboardButton("💳 Lihat Harga", callback_data="onboarding:pricing")],
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        # Tier check for callback queries
        user_id = query.from_user.id
        from src.bot.tier_gate import get_user_tier_sync
        user_tier = get_user_tier_sync(user_id)
        
        data = query.data
        
        # ── Onboarding Tour Steps ──────────────────────────────
        if data == "onboarding:start":
            await self._onboarding_step(update, context, 1)
            return
        elif data == "onboarding:step1":
            await self._onboarding_step(update, context, 2)
            return
        elif data == "onboarding:step2":
            await self._onboarding_step(update, context, 3)
            return
        elif data == "onboarding:step3":
            await self._onboarding_step(update, context, 4)
            return
        elif data == "onboarding:step4":
            await self._onboarding_step(update, context, 5)
            return
        elif data.startswith("panduan:"):
            page_str = data.split(":")[1]
            tier = context.user_data.get("panduan_tier", "free")
            badge = context.user_data.get("panduan_badge", "🆓")
            page = int(page_str)
            text, keyboard = self._panduan_page(page, tier, badge)
            await query.edit_message_text(
                text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        elif data == "onboarding:pricing":
            await self.pricing(update, context)
            return
        
        # ── Inline Screener Trigger ───────────────────────────
        elif data == "screener:momentum":
            await query.edit_message_text("🔍 Scanning momentum...")
            await self._run_category_screener(update, "momentum")
            return
        
        # ── Inline Alert Demo ─────────────────────────────────
        elif data == "alert_demo":
            text = (
                f"🔔 *Demo Alert — BBCA*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Kalau kamu pasang `alert BBCA >5600`,\n"
                f"bot otomatis kirim notifikasi ini\n"
                f"pas harga BBCA tembus 5.600.\n\n"
                f"📲 *Notifikasi dikirim via DM Telegram.*\n"
                f"🔁 Bot pantau setiap 15 menit.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 *Coba pasang alert sekarang:*\n"
                f"`alert BBCA >5600`\n\n"
                f"📊 /help — semua command"
            )
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[
                InlineKeyboardButton("← Kembali ke Tour", callback_data="onboarding:step2"),
                InlineKeyboardButton("Selesai →", callback_data="onboarding:step4"),
            ]]
            await query.edit_message_text(
                text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
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
        elif data.startswith("analisa:"):
            # Inline button: Analisa stock
            symbol = data.split(":")[1].upper()
            await query.edit_message_text(f"📊 Analisa {symbol}...", parse_mode="Markdown")
            # Run analysis
            try:
                await self.analyze(update, context, symbol)
                await query.edit_message_text(f"📊 Analisa {symbol} selesai! Cek di atas.")
            except Exception as e:
                await query.edit_message_text(f"❌ Gagal analisa {symbol}: {str(e)[:100]}")
            return
        elif data.startswith("plan:"):
            # Inline button: Create trading plan
            symbol = data.split(":")[1].upper()
            await query.edit_message_text(f"📋 Membuat plan {symbol}...", parse_mode="Markdown")
            # Run plan generation
            try:
                from src.engine.trading_plan import generate_trading_plan
                plan = await generate_trading_plan(symbol)
                await query.edit_message_text(plan, parse_mode="Markdown")
            except Exception as e:
                await query.edit_message_text(f"❌ Gagal membuat plan {symbol}: {str(e)[:100]}")
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
        if not await self._check_tier(update, "report"): return
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
        if not await self._check_tier(update, "trending"): return
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
        if not await self._check_tier(update, "news"): return
        args = context.args or []
        symbol = args[0].upper() if args else ""

        if not symbol:
            # General market news from ingestion pipeline
            msg = await update.message.reply_text("📰 Cari berita pasar...")
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
                    f"Sentimen: {score_emoji} *{report.score:.1f}/10* — {report.summary}\n"
                    f"Ada {report.total_articles} "
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
        if not await self._check_tier(update, "feedback"): return
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
                # ─── Gamification ──────────────────────────
                try:
                    from src.engine.gamification import award
                    award(update.effective_user.id, "feedback", update.effective_user.username or "")
                except Exception:
                    pass
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
        if not await self._check_tier(update, "upgrade"): return
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
        if not await self._check_tier(update, "bandarmology"): return
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

            out = f"🎰 *Aktivitas Bandar*\n"
            out += f"━━━━━━━━━━━━━━━━━━━━\n\n"
            out += f"{report.summary}\n\n"

            if report.foreign_accumulation_signals:
                out += "🟢 *Akumulasi Asing:*\n"
                for s in report.foreign_accumulation_signals[:5]:
                    out += f"  {s.broker_code} ({s.broker_name})\n"
                    out += f"  +Rp{s.net_value:,.0f} ({s.strength})\n"

            if report.foreign_distribution_signals:
                out += "\n🔴 *Distribusi Asing:*\n"
                for s in report.foreign_distribution_signals[:5]:
                    out += f"  {s.broker_code} ({s.broker_name})\n"
                    out += f"  -Rp{abs(s.net_value):,.0f} ({s.strength})\n"

            out += f"\n━━━━━━━━━━━━━━━━━━━━\n"
            out += f"💎 Premium: alert bandar real-time — /upgrade"

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
        if not await self._check_tier(update, "event"): return
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
                out += "\n\n💡 Potensi *POSITIF* — verifikasi: `analisa <kode>`"
            elif result["signal"] < 0:
                out += "\n\n⚠️ Potensi *NEGATIF* — verifikasi: `analisa <kode>`"

            out += "\n\n💎 FinBERT-ID classifier (95.2% akurasi)"
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
        if not await self._check_tier(update, "sector"): return
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
        if not await self._check_tier(update, "ihsg"): return
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
        if not await self._check_tier(update, "watchlist"): return
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
                if ok:
                    # ─── Gamification ──────────────────────
                    try:
                        from src.engine.gamification import award
                        award(update.effective_user.id, "watchlist_add", update.effective_user.username or "")
                    except Exception:
                        pass
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

    # ── Gamification ──

    async def leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show weekly leaderboard."""
        if not await self._check_tier(update, "leaderboard"): return
        try:
            from src.engine.gamification import GamificationEngine
            engine = GamificationEngine()
            entries = engine.get_leaderboard("weekly", 10)
            text = engine.format_leaderboard(entries, "weekly")
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Leaderboard error: {e}")
            await update.message.reply_text("❌ Gagal load leaderboard. Coba lagi.")

    async def points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's personal points."""
        if not await self._check_tier(update, "points"): return
        try:
            from src.engine.gamification import GamificationEngine
            engine = GamificationEngine()
            user_id = update.effective_user.id
            data = engine.get_points(user_id)
            text = engine.format_points(data)
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Points error: {e}")
            await update.message.reply_text("❌ Gagal load poin. Coba lagi.")

    # ── Category Screeners ──

    async def _run_category_screener(self, update: Update, category: str) -> None:
        """Run a category screener and display results."""
        from datetime import datetime
        
        # Dynamic stock count
        try:
            from src.engine.idx_universe import IDX_UNIVERSE
            stock_count = len(IDX_UNIVERSE)
        except:
            stock_count = 704
        
        try:
            from src.engine.screener_categories import CategoryScreener
            from src.engine.screener_cache import fetch_all_cached

            await update.message.reply_text(
                f"🔍 Scanning *{category}* — {stock_count} saham IDX...\n"
                f"⏳ Mohon tunggu ~5 detik",
                parse_mode="Markdown"
            )

            data = await fetch_all_cached()
            scanned = len(data)
            failed = stock_count - scanned
            
            screener = CategoryScreener(data)

            screen_map = {
                "momentum": screener.screen_momentum,
                "reversal": screener.screen_reversal,
                "breakout": screener.screen_breakout,
                "smartmoney": screener.screen_smartmoney,
            }

            if category not in screen_map:
                await update.message.reply_text("❌ Kategori tidak dikenal.")
                return

            result = screen_map[category](limit=10)

            if not result.hits:
                await update.message.reply_text(
                    f"📭 Belum ada saham yang cocok kategori *{result.category}* saat ini.\n\n"
                    f"💡 Coba: /screener_momentum atau /screener_reversal",
                    parse_mode="Markdown",
                )
                return

            # Header with scan stats
            now = datetime.now().strftime("%d %b %Y %H:%M")
            text = (
                f"🔍 *{result.category}*\n"
                f"{result.description}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 Di-scan: *{scanned}/{stock_count}* saham"
            )
            if failed > 0:
                text += f" ({failed} gagal fetch)"
            text += f"\n⏰ {now}\n\n"

            # Results with action buttons
            for i, h in enumerate(result.hits[:10], 1):
                emoji = "🟢" if h.change_pct > 0 else "🔴"
                score_emoji = "🔥" if h.score >= 80 else ("⭐" if h.score >= 60 else "📊")
                
                text += (
                    f"*{i}. {h.symbol}*  {emoji} Rp{h.price:,.0f} ({h.change_pct:+.1f}%)\n"
                    f"   {score_emoji} Score: *{h.score}/100*  |  {h.strategy}\n"
                )
                for r in h.reasons[:2]:
                    text += f"   └ {r}\n"
                text += "\n"

            # Score legend
            text += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📊 *Skor:*\n"
                "🔥 80-100 = Sinyal kuat\n"
                "⭐ 60-79 = Sinyal sedang\n"
                "📊 40-59 = Sinyal lemah\n\n"
            )

            # Quick actions
            text += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📌 *Langkah Selanjutnya:*\n"
                "• `analisa [KODE]` — lihat detail saham\n"
                "• `plan [KODE]` — buat trading plan\n"
                "• `alert [KODE] >harga` — pasang alert\n\n"
            )

            # Other screeners
            text += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📊 *Screener Lainnya:*\n"
                "• `screener momentum` — momentum kuat\n"
                "• `screener reversal` — siap balik arah\n"
                "• `screener breakout` — breakout terdeteksi\n"
                "• `screener smart money` — jejak akumulasi bandar"
            )

            # Add inline keyboard for top 3 stocks
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = []
            for h in result.hits[:3]:
                keyboard.append([
                    InlineKeyboardButton(
                        f"📊 Analisa {h.symbol}",
                        callback_data=f"analisa:{h.symbol}"
                    ),
                    InlineKeyboardButton(
                        f"📋 Plan {h.symbol}",
                        callback_data=f"plan:{h.symbol}"
                    )
                ])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                text, 
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

            # ── Log screener run to DB for dashboard ──
            try:
                import json
                from src.models import ScreenerLog, get_engine
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker

                sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
                eng = create_engine(sync_url)
                Sess = sessionmaker(bind=eng)
                with Sess() as sess:
                    hits_data = [{
                        "symbol": h.symbol,
                        "score": h.score,
                        "strategy": h.strategy,
                        "change_pct": h.change_pct,
                    } for h in result.hits[:10]]
                    log = ScreenerLog(
                        user_id=update.effective_user.id,
                        category=category,
                        total_scanned=scanned,
                        total_hits=result.total_signals,
                        hits_json=json.dumps(hits_data),
                    )
                    sess.add(log)
                    sess.commit()
                eng.dispose()
            except Exception as log_err:
                logger.warning(f"Screener log failed: {log_err}")

        except Exception as e:
            logger.warning(f"Category screener error: {e}")
            await update.message.reply_text(f"❌ Gagal screening: {str(e)[:100]}")

    async def screener_momentum(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_tier(update, "screener_momentum"): return
        await self._run_category_screener(update, "momentum")

    async def screener_reversal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_tier(update, "screener_reversal"): return
        await self._run_category_screener(update, "reversal")

    async def screener_breakout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_tier(update, "screener_breakout"): return
        await self._run_category_screener(update, "breakout")

    async def screener_smartmoney(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_tier(update, "screener_smartmoney"): return
        await self._run_category_screener(update, "smartmoney")

    # ── Portfolio Tracker ──

    async def portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Portfolio management: /portfolio [add|close|history] [symbol] [price] [qty]"""
        if not await self._check_tier(update, "portfolio"): return
        try:
            from src.engine.portfolio import PortfolioEngine
            engine = PortfolioEngine()
            user_id = update.effective_user.id
            args = context.args or []

            if not args:
                msg = await update.message.reply_text("📊 Loading portfolio...")
                positions = engine.load(user_id)
                positions = await engine.refresh_prices(positions)
                text = engine.format_portfolio(positions)
                await msg.edit_text(text, parse_mode="Markdown")
                return

            action = args[0].lower()

            if action == "add" and len(args) >= 4:
                symbol = args[1].upper()
                try:
                    entry_price = float(args[2])
                    quantity = int(args[3])
                except ValueError:
                    await update.message.reply_text("❌ Format harga/qty salah. Contoh: `/portfolio add BBCA 4500 100`")
                    return
                ok, msg = engine.add(user_id, symbol, entry_price, quantity)
                await update.message.reply_text(msg, parse_mode="Markdown")

            elif action == "close" and len(args) >= 3:
                symbol = args[1].upper()
                try:
                    exit_price = float(args[2])
                except ValueError:
                    await update.message.reply_text("❌ Format harga salah. Contoh: `/portfolio close BBCA 4800`")
                    return
                ok, msg = engine.close(user_id, symbol, exit_price)
                await update.message.reply_text(msg, parse_mode="Markdown")

            elif action == "history":
                positions = engine.load(user_id)
                text = engine.format_history(positions)
                await update.message.reply_text(text, parse_mode="Markdown")

            else:
                await update.message.reply_text(
                    "📊 *Portfolio*\n\n"
                    "`/portfolio` — lihat portfolio\n"
                    "`/portfolio add BBCA 4500 100` — tambah posisi\n"
                    "`/portfolio close BBCA 4800` — tutup posisi\n"
                    "`/portfolio history` — riwayat trading",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.warning(f"Portfolio error: {e}")
            await update.message.reply_text("❌ Gagal akses portfolio. Coba lagi.")

    async def jejak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Profit trail — Stockpick 'Jejak Cuan' style."""
        if not await self._check_tier(update, "jejak"): return
        try:
            from src.engine.portfolio import PortfolioEngine
            engine = PortfolioEngine()
            user_id = update.effective_user.id
            positions = engine.load(user_id)
            positions = await engine.refresh_prices(positions)
            text = engine.format_jejak(positions)
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Jejak error: {e}")
            await update.message.reply_text("❌ Gagal load jejak cuan. Coba lagi.")

    # ── Trading Journal ──

    async def journal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Trading journal: /journal [add|delete|list] [text|id]"""
        if not await self._check_tier(update, "journal"): return
        try:
            from src.engine.journal import JournalEngine
            engine = JournalEngine()
            user_id = update.effective_user.id
            args = context.args or []

            if not args:
                entries = engine.load(user_id)
                entries_sorted = sorted(entries, key=lambda e: e.timestamp, reverse=True)
                text = engine.format_entries(entries_sorted, page=1, per_page=5)
                await update.message.reply_text(text, parse_mode="Markdown")
                return

            action = args[0].lower()

            if action == "add":
                text = " ".join(args[1:]) if len(args) > 1 else ""
                if not text:
                    await update.message.reply_text(
                        "📓 Tambah catatan trading:\n"
                        "`/journal add TLKM entry 4500 exit 4800 — sabar nunggu pullback`\n\n"
                        "💡 Auto-detect #tags dan saham dari teks"
                    )
                    return
                ok, msg = engine.add(user_id, text)
                await update.message.reply_text(msg, parse_mode="Markdown")

            elif action == "delete" and len(args) >= 2:
                try:
                    entry_id = int(args[1])
                except ValueError:
                    await update.message.reply_text("❌ ID harus angka. Contoh: `/journal delete 3`")
                    return
                ok, msg = engine.delete(user_id, entry_id)
                await update.message.reply_text(msg)

            elif action == "list":
                page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
                entries = engine.load(user_id)
                entries_sorted = sorted(entries, key=lambda e: e.timestamp, reverse=True)
                text = engine.format_entries(entries_sorted, page=page)
                await update.message.reply_text(text, parse_mode="Markdown")

            else:
                await update.message.reply_text(
                    "📓 *Trading Journal*\n\n"
                    "`/journal` — lihat catatan terbaru\n"
                    "`/journal add <teks>` — tambah catatan\n"
                    "`/journal list` — semua catatan\n"
                    "`/journal delete <id>` — hapus",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.warning(f"Journal error: {e}")
            await update.message.reply_text("❌ Gagal akses journal. Coba lagi.")

    # ── Economic Calendar ──

    async def calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Economic calendar: /calendar [next|all]"""
        if not await self._check_tier(update, "calendar"): return
        try:
            from src.engine.eco_calendar import get_upcoming_events, get_events_for_month, format_calendar
            from datetime import datetime

            args = context.args or []
            action = args[0].lower() if args else ""

            if action == "next":
                now = datetime.now()
                if now.month == 12:
                    events = get_events_for_month(now.year + 1, 1)
                else:
                    events = get_events_for_month(now.year, now.month + 1)
                title = f"Bulan Depan ({now.month+1}/{now.year})"
            elif action == "all":
                events = get_upcoming_events(20)
                title = "All Upcoming Events"
            else:
                now = datetime.now()
                events = get_events_for_month(now.year, now.month)
                title = f"Bulan Ini — {now.strftime('%B %Y')}"

            text = format_calendar(events, title)
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Calendar error: {e}")
            await update.message.reply_text("❌ Gagal load calendar. Coba lagi.")

    # ── Market Breadth ──

    async def breadth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Market breadth: scan 39 IDX stocks for advance/decline, MA50, 52w H/L."""
        if not await self._check_tier(update, "breadth"): return
        msg = await update.message.reply_text("📊 Menghitung market breadth... (30-60 detik)")
        try:
            from src.engine.breadth import compute_breadth, format_breadth
            data = await compute_breadth()
            text = format_breadth(data)
            await msg.edit_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Breadth error: {e}")
            await msg.edit_text(f"❌ Gagal breadth: {str(e)[:100]}")

    async def premarket(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_tier(update, "premarket"): return
        mode = "compact" if context.args and context.args[0].lower() == "quick" else "full"
        msg = await update.message.reply_text("🌅 Ambil data pre-market... (15-30 detik)")
        try:
            from src.engine.premarket import build_premarket_snapshot, format_premarket, format_premarket_compact
            snapshot = await build_premarket_snapshot()
            if mode == "compact":
                text = format_premarket_compact(snapshot)
            else:
                text = format_premarket(snapshot)
            await msg.edit_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Premarket error: {e}", exc_info=True)
            await msg.edit_text(
                f"❌ Gagal pre-market briefing: {str(e)[:100]}\n\n"
                f"Coba lagi nanti atau `/premarket quick`"
            )

    async def briefing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Daily AI Briefing — morning market snapshot."""
        if not await self._check_tier(update, "briefing"): return
        msg = await update.message.reply_text("☀️ Nyusun briefing pasar... (30 detik)")
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

    # Register handlers — core commands first
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help))
    app.add_handler(CommandHandler("analisa", handlers.analisa_direct))
    app.add_handler(CommandHandler("stats", handlers.stats_direct))
    app.add_handler(CommandHandler("panduan", handlers.panduan))
    # Screener
    app.add_handler(CommandHandler("screener_momentum", handlers.screener_momentum))
    app.add_handler(CommandHandler("screener_reversal", handlers.screener_reversal))
    app.add_handler(CommandHandler("screener_breakout", handlers.screener_breakout))
    app.add_handler(CommandHandler("screener_smartmoney", handlers.screener_smartmoney))
    # Trading
    app.add_handler(CommandHandler("plan", handlers.myplans))
    app.add_handler(CommandHandler("myplans", handlers.myplans))
    app.add_handler(CommandHandler("alert", handlers.myalerts))
    app.add_handler(CommandHandler("myalerts", handlers.myalerts))
    app.add_handler(CommandHandler("portfolio", handlers.portfolio))
    app.add_handler(CommandHandler("jejak", handlers.jejak))
    app.add_handler(CommandHandler("journal", handlers.journal))
    # Market
    app.add_handler(CommandHandler("premarket", handlers.premarket))
    app.add_handler(CommandHandler("briefing", handlers.briefing))
    app.add_handler(CommandHandler("calendar", handlers.calendar))
    app.add_handler(CommandHandler("ihsg", handlers.ihsg))
    app.add_handler(CommandHandler("sector", handlers.sectorforecast))
    app.add_handler(CommandHandler("news", handlers.news))
    app.add_handler(CommandHandler("trending", handlers.trending))
    app.add_handler(CommandHandler("breadth", handlers.breadth))
    app.add_handler(CommandHandler("bandarmology", handlers.bandarmology))
    app.add_handler(CommandHandler("event", handlers.event))
    app.add_handler(CommandHandler("report", handlers.report))
    # Account
    app.add_handler(CommandHandler("watchlist", handlers.watchlist))
    app.add_handler(CommandHandler("performance", handlers.performance))
    app.add_handler(CommandHandler("feedback", handlers.feedback))
    app.add_handler(CommandHandler("leaderboard", handlers.leaderboard))
    app.add_handler(CommandHandler("points", handlers.points))
    app.add_handler(CommandHandler("pricing", handlers.pricing))
    app.add_handler(CommandHandler("upgrade", handlers.upgrade))
    # NLP fallback — last handler
    app.add_handler(MessageHandler(filters.TEXT, handlers.handle_message))
    app.add_handler(CallbackQueryHandler(handlers.button_callback))

    return app


# ── Telegram Bot Command Menu ───────────────────────────────────

COMMANDS = [
    # Core
    ("start", "Menu utama & status"),
    ("help", "Semua command"),
    ("panduan", "Panduan lengkap (→ /help)"),
    ("analisa", "Analisa saham — ex: /analisa BBCA"),
    ("stats", "Statistik saham — ex: /stats TLKM"),
    # Screening
    ("screener_momentum", "Saham momentum kuat"),
    ("screener_reversal", "Saham siap reversal"),
    ("screener_breakout", "Saham breakout kunci"),
    ("screener_smartmoney", "Jejak akumulasi bandar"),
    # Trading
    ("plan", "Trading plan — ex: /plan TLKM"),
    ("myplans", "Lihat plan aktif"),
    ("alert", "Harga alert — ex: /alert TLKM >4600"),
    ("myalerts", "Lihat alert aktif"),
    ("portfolio", "Portfolio — add/close/status"),
    ("jejak", "Jejak Cuan profit trail"),
    ("journal", "Trading journal"),
    # Market
    ("premarket", "Pre-market global snapshot"),
    ("briefing", "Daily market briefing"),
    ("calendar", "Kalender ekonomi"),
    ("ihsg", "Data IHSG real-time"),
    ("sector", "Forecast 11 sektor IDX"),
    ("news", "Berita pasar terbaru"),
    ("trending", "Saham trending minggu ini"),
    ("breadth", "Market breadth A/D ratio"),
    ("bandarmology", "Deteksi akumulasi bandar"),
    ("event", "Event classifier korporat"),
    ("report", "Weekly report"),
    # Account
    ("watchlist", "Watchlist saham favorit"),
    ("performance", "Performa trading"),
    ("feedback", "Rating analisa — ex: /feedback BBCA 7"),
    ("leaderboard", "Top trader minggu ini"),
    ("points", "Poin & rank kamu"),
    ("pricing", "Paket langganan"),
    ("upgrade", "Upgrade ke Pro/Premium"),
]
