"""FastAPI web dashboard."""
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="IDX AI Trading Bot", version="0.1.0")

# Register webhook routes
from src.web.webhook import router as webhook_router
app.include_router(webhook_router)

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


@app.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin tracking dashboard — live stats."""
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine, func
    from sqlalchemy.orm import sessionmaker
    from src.models import User, Subscription, AnalysisJournal, Alert, TradePlan

    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week = today - timedelta(days=today.weekday())

        total_users = session.query(func.count(User.id)).scalar() or 0
        new_today = session.query(func.count(User.id)).filter(User.created_at >= today).scalar() or 0

        subs = dict(session.query(Subscription.tier, func.count(Subscription.id)).group_by(Subscription.tier).all())
        pro = subs.get("pro", 0)
        premium = subs.get("premium", 0)

        analyses_today = session.query(func.count(AnalysisJournal.id)).filter(AnalysisJournal.timestamp >= today).scalar() or 0
        analyses_week = session.query(func.count(AnalysisJournal.id)).filter(AnalysisJournal.timestamp >= week).scalar() or 0

        active_alerts = session.query(func.count(Alert.id)).filter(Alert.is_active == True, Alert.is_triggered == False).scalar() or 0
        active_plans = session.query(func.count(TradePlan.id)).filter(TradePlan.status == "active").scalar() or 0

        revenue = pro * 49000 + premium * 149000

    engine.dispose()

    cards = [
        ("👥 Total User", total_users, f"+{new_today} hari ini"),
        ("💰 Revenue/bln", f"Rp{revenue:,}", f"{pro + premium} berbayar"),
        ("📊 Analisa Hari Ini", analyses_today, f"{analyses_week} minggu ini"),
        ("🔔 Alert Aktif", active_alerts, f"{active_plans} plan"),
    ]

    cards_html = ""
    for title, value, sub in cards:
        cards_html += f"""
        <div class="card">
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
            <div class="card-sub">{sub}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vilona Saham — Dashboard</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    background: #0a0a0a;
    color: #e0e0e0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh;
    padding: 2rem;
}}
.container {{ max-width: 1100px; margin: 0 auto; }}
h1 {{
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    background: linear-gradient(135deg, #00f0ff, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.subtitle {{ color: #888; margin-bottom: 2rem; font-size: 0.95rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
.card {{
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1.5rem;
    backdrop-filter: blur(10px);
}}
.card:hover {{ border-color: rgba(0,240,255,0.3); }}
.card-title {{ font-size: 0.85rem; color: #888; margin-bottom: 0.5rem; }}
.card-value {{ font-size: 2rem; font-weight: 700; background: linear-gradient(135deg, #00f0ff, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.card-sub {{ font-size: 0.8rem; color: #666; margin-top: 0.3rem; }}
.section {{ margin-bottom: 2rem; }}
.section-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; color: #aaa; }}
.api-link {{
    display: inline-block;
    margin-top: 1rem;
    padding: 0.6rem 1.2rem;
    background: rgba(0,240,255,0.1);
    border: 1px solid rgba(0,240,255,0.2);
    border-radius: 8px;
    color: #00f0ff;
    text-decoration: none;
    font-size: 0.85rem;
}}
.api-link:hover {{ background: rgba(0,240,255,0.15); }}
.refresh {{ color: #666; font-size: 0.8rem; margin-top: 2rem; }}
</style>
</head>
<body>
<div class="container">
    <h1>⚡ Vilona Saham</h1>
    <p class="subtitle">Admin Dashboard — Live Stats</p>

    <div class="grid">
        {cards_html}
    </div>

    <div class="section">
        <div class="section-title">📡 API Endpoints</div>
        <a class="api-link" href="/api/stats">📊 /api/stats — Full JSON</a>
        <a class="api-link" href="/api/health">🫀 /api/health — Status</a>
    </div>

    <p class="refresh">Auto-refresh: 60 detik</p>
</div>
<script>
setTimeout(() => location.reload(), 60000);
</script>
</body>
</html>"""

    return HTMLResponse(html)

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/capi")
async def capi(request: Request):
    """Proxy Conversions API events to Meta via phantomfx backend.
    Browser sends events here so the domain stays botidx.aitradepulse.com."""
    import httpx
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://phantomfx.aitradepulse.com/api/capi",
                json=body,
                headers={"Content-Type": "application/json"},
            )
        return {"status": "ok", "proxy_status": resp.status_code}
    except Exception as e:
        logger.warning(f"CAPI proxy error: {e}")
        return {"status": "error", "detail": str(e)}


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
                sub_counts.get("pro", 0) * 49000
                + sub_counts.get("premium", 0) * 149000
            ),
        },
    }
