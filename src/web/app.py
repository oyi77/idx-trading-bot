"""FastAPI web dashboard."""
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.config import settings

logger = logging.getLogger(__name__)

# Import CAPI bridge
from src.web.capi_bridge import handle_capi

app = FastAPI(title="IDX AI Trading Bot", version="0.1.0")

# Register webhook routes
from src.web.webhook import router as webhook_router
app.include_router(webhook_router)

# Register admin dashboard routes
from src.web.admin import register_admin_routes
register_admin_routes(app)

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)

# Optional Jinja2 templates
templates = None
try:
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
except ImportError:
    logger.warning("jinja2 not installed — dashboard templates disabled")

# ── API Routes ──

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    from src.web.landing import LANDING_HTML
    return HTMLResponse(LANDING_HTML)

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# CAPI endpoint — handled by bridge module
app.add_api_route("/api/capi", handle_capi, methods=["POST"])


@app.get("/api/market-overview")
async def market_overview():
    """Top IDX stocks overview for dashboard."""
    symbols = ["BBCA", "BBRI", "TLKM", "BMRI", "BBNI", "UNVR", "ASII"]
    from src.feed.yahoo import YahooFeed
    feed = YahooFeed()
    results = []
    for sym in symbols:
        try:
            q = await feed.get_quote(sym)
            if q:
                results.append({
                    "symbol": sym,
                    "price": q["price"],
                    "change": q.get("change_pct", 0),
                    "volume": q.get("volume", 0),
                })
        except Exception:
            pass
    return {"stocks": results, "count": len(results)}

@app.get("/api/screener-stats")
async def screener_stats():
    """Screener activity for dashboard — today's runs + latest hits."""
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine, func
    from sqlalchemy.orm import sessionmaker
    from src.models import ScreenerLog
    import json

    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        runs_today = session.query(func.count(ScreenerLog.id)).filter(
            ScreenerLog.timestamp >= today
        ).scalar() or 0

        # Per-category counts
        by_cat = session.query(
            ScreenerLog.category, func.count(ScreenerLog.id)
        ).filter(ScreenerLog.timestamp >= today).group_by(ScreenerLog.category).all()
        categories = {c: n for c, n in by_cat}

        total_hits_today = session.query(func.sum(ScreenerLog.total_hits)).filter(
            ScreenerLog.timestamp >= today
        ).scalar() or 0

        # Latest run
        latest = session.query(ScreenerLog).order_by(
            ScreenerLog.timestamp.desc()
        ).first()

    engine.dispose()

    result = {
        "runs_today": runs_today,
        "total_hits_today": total_hits_today,
        "by_category": categories,
    }

    if latest:
        try:
            hits = json.loads(latest.hits_json) if latest.hits_json else []
        except json.JSONDecodeError:
            hits = []
        result["latest"] = {
            "category": latest.category,
            "scanned": latest.total_scanned,
            "hits_count": latest.total_hits,
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
            "top_hits": hits[:5],
        }

    return result

@app.get("/api/quote/{symbol}")
async def get_quote(symbol: str):
    from src.feed.yahoo import YahooFeed
    feed = YahooFeed()
    result = await feed.get_quote(symbol.upper())
    if result:
        return {"symbol": symbol.upper(), "data": result}
    return {"error": "Not found"}

@app.get("/api/analyze/{symbol}")
async def analyze(symbol: str):
    """Full analysis endpoint."""
    from src.feed.manager import FeedManager
    from src.engine.technical import TechnicalEngine

    feed = FeedManager()
    quote = await feed.get_quote(symbol.upper())
    klines = await feed.get_klines(symbol.upper(), "1d", 100)

    if not klines:
        return {"error": "No data"}

    closes = [k.close for k in klines]
    highs = [k.high for k in klines]
    lows = [k.low for k in klines]
    volumes = [k.volume for k in klines]

    tech = TechnicalEngine()
    analysis = tech.analyze(symbol.upper(), closes, highs, lows, volumes)
    score, reasons = tech.combined_score(closes, highs, lows, volumes)

    return {
        "symbol": symbol.upper(),
        "price": quote.price if quote else closes[-1],
        "score": score,
        "reasons": reasons,
        "analysis": analysis,
    }


@app.get("/api/stats")
async def dashboard_stats():
    """Real-time tracking dashboard — users, subscriptions, analyses, accuracy."""
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine, func, text
    from sqlalchemy.orm import sessionmaker

    from src.models import User, Subscription, AnalysisJournal, Alert, TradePlan

    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        # Users
        total_users = session.query(func.count(User.id)).scalar() or 0
        new_today = session.query(func.count(User.id)).filter(
            User.created_at >= today_start
        ).scalar() or 0

        # Subscriptions
        subs = session.query(Subscription.tier, func.count(Subscription.id)).group_by(
            Subscription.tier
        ).all()
        sub_counts = {t: c for t, c in subs}

        # Analyses
        total_analyses = session.query(func.count(AnalysisJournal.id)).scalar() or 0
        analyses_today = session.query(func.count(AnalysisJournal.id)).filter(
            AnalysisJournal.timestamp >= today_start
        ).scalar() or 0
        analyses_week = session.query(func.count(AnalysisJournal.id)).filter(
            AnalysisJournal.timestamp >= week_start
        ).scalar() or 0

        # Accuracy (resolved analyses)
        resolved = session.query(
            func.count(AnalysisJournal.id)
        ).filter(AnalysisJournal.resolved == True).scalar() or 0
        accurate = session.query(
            func.count(AnalysisJournal.id)
        ).filter(
            AnalysisJournal.resolved == True,
            AnalysisJournal.accuracy_pct > 0,
        ).scalar() or 0
        # AI accuracy = % resolved where accuracy > 0 (correct prediction)
        total_with_result = session.query(func.count(AnalysisJournal.id)).filter(
            AnalysisJournal.resolved == True,
            AnalysisJournal.accuracy_pct.isnot(None),
        ).scalar() or 0
        accurate_count = session.query(func.count(AnalysisJournal.id)).filter(
            AnalysisJournal.resolved == True,
            AnalysisJournal.accuracy_pct > 0,
        ).scalar() or 0
        ai_accuracy = round(accurate_count / total_with_result * 100, 1) if total_with_result > 0 else 0

        # Active alerts & plans
        active_alerts = session.query(func.count(Alert.id)).filter(
            Alert.is_active == True,
            Alert.is_triggered == False,
        ).scalar() or 0
        active_plans = session.query(func.count(TradePlan.id)).filter(
            TradePlan.status == "active",
        ).scalar() or 0

        # Signals today
        signals = session.query(AnalysisJournal.signal, func.count(AnalysisJournal.id)).filter(
            AnalysisJournal.timestamp >= today_start
        ).group_by(AnalysisJournal.signal).all()
        signal_counts = {s: c for s, c in signals}

        # Top symbols analyzed today
        top_symbols = session.query(
            AnalysisJournal.symbol, func.count(AnalysisJournal.id).label("cnt")
        ).filter(
            AnalysisJournal.timestamp >= today_start
        ).group_by(AnalysisJournal.symbol).order_by(
            func.count(AnalysisJournal.id).desc()
        ).limit(5).all()

    engine.dispose()

    return {
        "status": "ok",
        "timestamp": now.isoformat(),
        "users": {
            "total": total_users,
            "new_today": new_today,
            "by_tier": {
                "free": sub_counts.get("free", 0),
                "pro": sub_counts.get("pro", 0),
                "premium": sub_counts.get("premium", 0),
                "lifetime": sub_counts.get("lifetime", 0),
            },
        },
        "activity": {
            "total_analyses": total_analyses,
            "analyses_today": analyses_today,
            "analyses_this_week": analyses_week,
            "active_alerts": active_alerts,
            "active_plans": active_plans,
            "signals_today": signal_counts,
            "top_symbols_today": [{"symbol": s, "count": c} for s, c in top_symbols],
        },
        "ai": {
            "accuracy_pct": ai_accuracy,
            "total_resolved": total_with_result,
        },
        "revenue": {
            "pro_count": sub_counts.get("pro", 0),
            "premium_count": sub_counts.get("premium", 0),
            "lifetime_count": sub_counts.get("lifetime", 0),
            "estimated_monthly": (
                sub_counts.get("pro", 0) * 79900
                + sub_counts.get("premium", 0) * 149900
            ),
        },
    }
