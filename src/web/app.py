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

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


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
