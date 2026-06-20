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

@app.post("/api/checkout")
async def scalev_checkout(request: Request):
    """Create ScaleV order for Vilona Saham subscription."""
    import json, urllib.request, time, os
    try:
        body = await request.body()
        data = json.loads(body)
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    tier = data.get("tier", "pro")
    if not name or not phone:
        return JSONResponse({"error": "name and phone required"}, status_code=400)

    API_KEY = os.getenv("SCALEV_API_KEY", "sk_4gv9dCXRFQkk9UYIN7S2Z2GPj1QBZ1NI7kR3tkdjCLalkvIK8A4cKX8ICax03WDL")
    STORE_ID = "store_xdK72UFPYZRo8zvgOmdFgYeP"
    VARIANTS = {
        "pro": "variant_POFUXCGJ-njxt1lwEw1JaMpQ",
        "premium": "variant_hnXIRBhirz1u-MdLMMazOnxk",
        "lifetime": "variant__YDBbPxqyG-yp3g2akUxQoE8",
    }

    variant_id = VARIANTS.get(tier, VARIANTS["pro"])
    clean_phone = phone.lstrip("0") if phone.startswith("0") else phone
    if not clean_phone.startswith("62"):
        clean_phone = "62" + clean_phone

    payload = json.dumps({
        "store_unique_id": STORE_ID,
        "customer_name": name,
        "customer_phone": clean_phone,
        "ordervariants": [{"quantity": 1, "variant_unique_id": variant_id}],
        "payment_method": "qris",
        "metadata": {"telegram_username": name, "tier": tier},
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.scalev.com/v3/orders",
            data=payload, method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {API_KEY}")
        req.add_header("User-Agent", "Mozilla/5.0 VilonaBot/1.0")
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        logger.info(f"ScaleV order: {result.get('order_id')} tier={tier}")
        return JSONResponse(result)
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        logger.error(f"ScaleV error {e.code}: {body_err}")
        return JSONResponse({"error": f"ScaleV error {e.code}", "detail": body_err}, status_code=e.code)
    except Exception as e:
        logger.error(f"ScaleV error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Premium cinematic admin dashboard — particles, glassmorphism, live data."""
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
        free = subs.get("free", 0)
        lifetime = subs.get("lifetime", 0)

        analyses_today = session.query(func.count(AnalysisJournal.id)).filter(AnalysisJournal.timestamp >= today).scalar() or 0
        analyses_week = session.query(func.count(AnalysisJournal.id)).filter(AnalysisJournal.timestamp >= week).scalar() or 0
        total_analyses = session.query(func.count(AnalysisJournal.id)).scalar() or 0

        active_alerts = session.query(func.count(Alert.id)).filter(Alert.is_active == True, Alert.is_triggered == False).scalar() or 0
        active_plans = session.query(func.count(TradePlan.id)).filter(TradePlan.status == "active").scalar() or 0

        # Resolved accuracy
        total_resolved = session.query(func.count(AnalysisJournal.id)).filter(
            AnalysisJournal.resolved == True, AnalysisJournal.accuracy_pct.isnot(None)
        ).scalar() or 0
        accurate = session.query(func.count(AnalysisJournal.id)).filter(
            AnalysisJournal.resolved == True, AnalysisJournal.accuracy_pct > 0
        ).scalar() or 0
        ai_acc = round(accurate / total_resolved * 100, 1) if total_resolved > 0 else 0

        revenue = pro * 79900 + premium * 149900

        # Top symbols
        top_syms = session.query(
            AnalysisJournal.symbol, func.count(AnalysisJournal.id).label("cnt")
        ).filter(AnalysisJournal.timestamp >= today).group_by(
            AnalysisJournal.symbol
        ).order_by(func.count(AnalysisJournal.id).desc()).limit(8).all()

    engine.dispose()

    import json
    top_json = json.dumps([{"symbol": s, "count": c} for s, c in top_syms])

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vilona Saham — Live Dashboard</title>
<style>
:root {{
    --cyan: #00f0ff;
    --purple: #a855f7;
    --amber: #f59e0b;
    --bg: #000000;
    --surface: rgba(255,255,255,0.03);
    --border: rgba(255,255,255,0.06);
    --text: #c8c8c8;
    --text-dim: #666;
}}

* {{ margin:0; padding:0; box-sizing:border-box; }}

body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
}}

/* ── Canvas Particle Background ── */
#particles {{
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
}}

/* ── Cursor Glow ── */
.cursor-glow {{
    position: fixed;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(0,240,255,0.06) 0%, rgba(168,85,247,0.03) 40%, transparent 70%);
    pointer-events: none;
    z-index: 1;
    transform: translate(-50%, -50%);
    transition: opacity 0.3s;
}}

/* ── Main Layout ── */
.container {{
    position: relative;
    z-index: 2;
    max-width: 1280px;
    margin: 0 auto;
    padding: 2.5rem 2rem;
}}

/* ── Header ── */
.header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2.5rem;
    flex-wrap: wrap;
    gap: 1rem;
}}

.logo-section h1 {{
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, var(--cyan) 0%, var(--purple) 50%, var(--cyan) 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 3s ease infinite;
}}

@keyframes shimmer {{
    0%, 100% {{ background-position:0% center; }}
    50% {{ background-position:200% center; }}
}}

.status-row {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: #888;
    margin-top: 0.3rem;
}}

.pulse {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 12px #22c55e;
    animation: pulse 2s ease-in-out infinite;
}}

@keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.5; transform: scale(1.5); }}
}}

.live-badge {{
    font-size: 0.7rem;
    padding: 0.3rem 0.7rem;
    border-radius: 100px;
    background: rgba(34,197,94,0.1);
    border: 1px solid rgba(34,197,94,0.3);
    color: #22c55e;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
}}

/* ── Stats Grid ── */
.stats-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}}

@media (max-width: 900px) {{
    .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}

@media (max-width: 500px) {{
    .stats-grid {{ grid-template-columns: 1fr; }}
}}

/* ── Glass Card ── */
.card {{
    position: relative;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
}}

.card::before {{
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 16px;
    padding: 1px;
    background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(0,240,255,0.05));
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
}}

.card:hover {{
    border-color: rgba(0,240,255,0.2);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 80px rgba(0,240,255,0.05);
}}

.card-label {{
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    margin-bottom: 0.6rem;
    font-weight: 500;
}}

.card-value {{
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, var(--cyan), var(--purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
}}

.card-context {{
    font-size: 0.8rem;
    color: var(--text-dim);
    margin-top: 0.4rem;
}}

.card-context .positive {{ color: #22c55e; }}
.card-context .negative {{ color: #ef4444; }}

/* ── Two-Column Section ── */
.section-grid {{
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
}}

@media (max-width: 900px) {{
    .section-grid {{ grid-template-columns: 1fr; }}
}}

/* ── Ticker Ribbon ── */
.ticker-card {{
    margin-bottom: 1.5rem;
}}

.ticker-ribbon {{
    display: flex;
    gap: 2rem;
    overflow: hidden;
    white-space: nowrap;
}}

.ticker-item {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.85rem;
    font-weight: 500;
}}

.ticker-sym {{
    color: #fff;
    font-weight: 700;
}}

.ticker-price {{
    color: var(--text);
}}

.ticker-change {{
    font-weight: 600;
}}

.ticker-change.up {{ color: #22c55e; }}
.ticker-change.down {{ color: #ef4444; }}

/* ── Top Symbols Table ── */
.symbol-list {{
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}}

.symbol-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}}

.symbol-row:last-child {{ border-bottom: none; }}

.symbol-name {{
    font-weight: 600;
    color: #fff;
    font-size: 0.9rem;
}}

.symbol-count {{
    font-size: 0.85rem;
    color: var(--text-dim);
}}

.symbol-bar {{
    height: 3px;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--cyan), var(--purple));
    margin-top: 0.25rem;
}}

/* ── Accuracy Gauge ── */
.gauge-section {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.8rem;
}}

.gauge-ring {{
    position: relative;
    width: 120px;
    height: 120px;
}}

.gauge-ring svg {{
    transform: rotate(-90deg);
}}

.gauge-value {{
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--cyan), var(--purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.gauge-label {{
    font-size: 0.8rem;
    color: var(--text-dim);
    text-align: center;
}}

/* ── Footer ── */
.footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 2rem;
    border-top: 1px solid rgba(255,255,255,0.04);
    flex-wrap: wrap;
    gap: 1rem;
}}

.footer-links {{
    display: flex;
    gap: 1.5rem;
}}

.footer-links a {{
    color: var(--text-dim);
    text-decoration: none;
    font-size: 0.8rem;
    transition: color 0.2s;
}}

.footer-links a:hover {{ color: var(--cyan); }}

.footer-time {{
    font-size: 0.8rem;
    color: var(--text-dim);
}}
</style>
</head>
<body>

<!-- Particle Canvas -->
<canvas id="particles"></canvas>

<!-- Cursor Glow -->
<div class="cursor-glow" id="cursorGlow"></div>

<div class="container">
    <!-- Header -->
    <div class="header">
        <div class="logo-section">
            <h1>Vilona Saham</h1>
            <div class="status-row">
                <div class="pulse"></div>
                <span>System Online</span>
                <span class="live-badge">LIVE</span>
            </div>
        </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid" id="statsGrid">
        <div class="card">
            <div class="card-label">Total Users</div>
            <div class="card-value" data-target="{total_users}">0</div>
            <div class="card-context"><span class="positive">+{new_today}</span> hari ini</div>
        </div>
        <div class="card">
            <div class="card-label">Revenue Estimasi</div>
            <div class="card-value" data-target="{revenue // 1000}">0</div>
            <div class="card-context">Rp{revenue:,}/bln · {pro + premium + lifetime} berbayar</div>
        </div>
        <div class="card">
            <div class="card-label">Analisa Hari Ini</div>
            <div class="card-value" data-target="{analyses_today}">0</div>
            <div class="card-context">{total_analyses:,} total · {analyses_week} minggu ini</div>
        </div>
        <div class="card">
            <div class="card-label">Alert & Plan Aktif</div>
            <div class="card-value" data-target="{active_alerts + active_plans}">0</div>
            <div class="card-context">{active_alerts} alert · {active_plans} plan</div>
        </div>
    </div>

    <!-- Two-Column: Top Symbols + Accuracy -->
    <div class="section-grid">
        <div class="card" id="topSymbols">
            <div class="card-label">Top Analisa Hari Ini</div>
            <div class="symbol-list"></div>
        </div>
        <div class="card">
            <div class="card-label">AI Accuracy</div>
            <div class="gauge-section">
                <div class="gauge-ring">
                    <svg width="120" height="120" viewBox="0 0 120 120">
                        <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="8"/>
                        <circle cx="60" cy="60" r="52" fill="none" stroke="url(#gaugeGrad)" stroke-width="8"
                            stroke-dasharray="{ai_acc * 3.267:.0f} 326.7" stroke-linecap="round" id="gaugeArc"/>
                        <defs>
                            <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stop-color="#00f0ff"/>
                                <stop offset="100%" stop-color="#a855f7"/>
                            </linearGradient>
                        </defs>
                    </svg>
                    <div class="gauge-value">{ai_acc}%</div>
                </div>
                <div class="gauge-label">{total_resolved} prediksi ter-resolve</div>
            </div>
        </div>
    </div>

    <!-- Screener Activity -->
    <div class="section-grid" id="screenerSection">
        <div class="card" id="screenerStats">
            <div class="card-label">Screener Hari Ini</div>
            <div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">
                <div>
                    <div class="card-value" style="font-size:2rem;" id="scrRuns">-</div>
                    <div class="card-context">runs</div>
                </div>
                <div>
                    <div class="card-value" style="font-size:2rem;" id="scrHits">-</div>
                    <div class="card-context">total hits</div>
                </div>
            </div>
            <div id="scrCategories" style="display:flex;gap:0.8rem;margin-top:0.8rem;flex-wrap:wrap;"></div>
        </div>
        <div class="card" id="screenerLatest">
            <div class="card-label">Latest Screener Hits</div>
            <div class="symbol-list" id="scrLatestHits">
                <div style="color:#666;font-size:0.85rem;text-align:center;padding:1rem;">Belum ada screener run</div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        <div class="footer-links">
            <a href="/api/stats">API Stats</a>
            <a href="/api/health">Health</a>
            <a href="https://t.me/vilonidxbot">Bot Telegram</a>
        </div>
        <div class="footer-time" id="clock"></div>
    </div>
</div>

<script>
const TOP_SYMBOLS = {top_json};

// ── Particles ──
const canvas = document.getElementById('particles');
const ctx = canvas.getContext('2d');
let particles = [];

function resize() {{
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}}
resize();
window.addEventListener('resize', resize);

class Particle {{
    constructor() {{
        this.reset();
        this.y = Math.random() * canvas.height;
    }}
    reset() {{
        this.x = Math.random() * canvas.width;
        this.y = -10;
        this.size = Math.random() * 2 + 0.5;
        this.speed = Math.random() * 0.4 + 0.1;
        this.opacity = Math.random() * 0.5 + 0.1;
        this.hue = Math.random() > 0.5 ? '0,240,255' : '168,85,247';
    }}
    update() {{
        this.y += this.speed;
        this.x += Math.sin(this.y * 0.01) * 0.3;
        if (this.y > canvas.height + 10) this.reset();
    }}
    draw() {{
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${{this.hue}},${{this.opacity}})`;
        ctx.fill();
    }}
}}

for (let i = 0; i < 80; i++) {{
    particles.push(new Particle());
}}

function animate() {{
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {{ p.update(); p.draw(); }});
    requestAnimationFrame(animate);
}}
animate();

// ── Cursor Glow ──
const glow = document.getElementById('cursorGlow');
document.addEventListener('mousemove', e => {{
    glow.style.left = e.clientX + 'px';
    glow.style.top = e.clientY + 'px';
    glow.style.opacity = '1';
}});
document.addEventListener('mouseleave', () => glow.style.opacity = '0');

// ── Count-Up Animation ──
function countUp(el) {{
    const target = parseInt(el.dataset.target);
    if (!target) return;
    const duration = 1200;
    const start = performance.now();
    function update(ts) {{
        const progress = Math.min((ts - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(eased * target);
        el.textContent = current.toLocaleString();
        if (progress < 1) requestAnimationFrame(update);
    }}
    requestAnimationFrame(update);
}}

document.querySelectorAll('.card-value[data-target]').forEach(countUp);

// ── Top Symbols ──
(function() {{
    const container = document.getElementById('topSymbols').querySelector('.symbol-list');
    if (!TOP_SYMBOLS.length) {{
        container.innerHTML = '<div style="color:#666;font-size:0.85rem;text-align:center;padding:1rem;">Belum ada analisa hari ini</div>';
        return;
    }}
    const maxCount = TOP_SYMBOLS[0].count;
    TOP_SYMBOLS.forEach(s => {{
        const row = document.createElement('div');
        row.className = 'symbol-row';
        row.innerHTML = `
            <div>
                <div class="symbol-name">${{s.symbol}}</div>
                <div class="symbol-bar" style="width:${{(s.count / maxCount * 100)}}%"></div>
            </div>
            <div class="symbol-count">${{s.count}}x</div>
        `;
        container.appendChild(row);
    }});
}})();

// ── Live Clock ──
function updateClock() {{
    const now = new Date();
    document.getElementById('clock').textContent =
        'WIB ' + now.toLocaleTimeString('id-ID', {{ hour:'2-digit', minute:'2-digit', second:'2-digit' }});
}}
updateClock();
setInterval(updateClock, 1000);

// ── Live Polling (no full refresh) ──
async function refreshStats() {{
    try {{
        const res = await fetch('/api/stats');
        const d = await res.json();
        // Update cards
        const cards = document.querySelectorAll('#statsGrid .card');
        if (cards.length >= 4) {{
            const vals = [
                d.users.total,
                d.revenue.estimated_monthly / 1000,
                d.activity.analyses_today,
                (d.activity.active_alerts || 0) + (d.activity.active_plans || 0)
            ];
            const ctxs = [
                `<span class="${{d.users.new_today > 0 ? 'positive' : ''}}">+${{d.users.new_today}}</span> hari ini`,
                `Rp${{d.revenue.estimated_monthly.toLocaleString()}}/bln · ${{d.revenue.pro_count + d.revenue.premium_count + d.revenue.lifetime_count}} berbayar`,
                `${{d.activity.total_analyses.toLocaleString()}} total · ${{d.activity.analyses_this_week}} minggu ini`,
                `${{d.activity.active_alerts}} alert · ${{d.activity.active_plans}} plan`
            ];
            vals.forEach((v, i) => {{
                const el = cards[i].querySelector('.card-value');
                const ctx = cards[i].querySelector('.card-context');
                if (el) {{ el.dataset.target = v; countUp(el); }}
                if (ctx) ctx.innerHTML = ctxs[i];
            }});
        }}
        // Update accuracy gauge
        const accPct = d.ai.accuracy_pct || 0;
        const gaugeArc = document.getElementById('gaugeArc');
        if (gaugeArc) {{
            gaugeArc.setAttribute('stroke-dasharray', `${{accPct * 3.267}} 326.7`);
        }}
        const gaugeVal = document.querySelector('.gauge-value');
        if (gaugeVal) gaugeVal.textContent = accPct + '%';
        const gaugeLab = document.querySelector('.gauge-label');
        if (gaugeLab) gaugeLab.textContent = `${{d.ai.total_resolved}} prediksi ter-resolve`;
    }} catch(e) {{}}
}}
setInterval(refreshStats, 15000);

// ── Screener Stats Refresh ──
async function refreshScreener() {{
    try {{
        const res = await fetch('/api/screener-stats');
        const d = await res.json();

        // Runs today
        const scrRuns = document.getElementById('scrRuns');
        if (scrRuns) scrRuns.textContent = d.runs_today || 0;

        // Total hits
        const scrHits = document.getElementById('scrHits');
        if (scrHits) scrHits.textContent = d.total_hits_today || 0;

        // Category badges
        const scrCat = document.getElementById('scrCategories');
        if (scrCat && d.by_category) {{
            const cats = ['momentum','reversal','breakout','smartmoney'];
            const icons = {{momentum:'🔥', reversal:'🔄', breakout:'💥', smartmoney:'🐋'}};
            scrCat.innerHTML = cats.map(c => {{
                const count = d.by_category[c] || 0;
                const alpha = count > 0 ? '1' : '0.3';
                return `<span style="font-size:0.75rem;padding:0.25rem 0.6rem;border-radius:100px;
                    background:rgba(0,240,255,0.08);border:1px solid rgba(0,240,255,0.15);
                    color:#c8c8c8;opacity:${{alpha}}">${{icons[c]}} ${{c}} ${{count}}x</span>`;
            }}).join('');
        }}

        // Latest hits
        const scrLatest = document.getElementById('scrLatestHits');
        if (scrLatest && d.latest && d.latest.top_hits.length) {{
            scrLatest.innerHTML = d.latest.top_hits.map(h => `
                <div class="symbol-row">
                    <div>
                        <div class="symbol-name">${{h.symbol}} <span style="font-size:0.7rem;color:#888;">${{h.strategy}}</span></div>
                        <div class="symbol-bar" style="width:${{h.score}}%"></div>
                    </div>
                    <div class="symbol-count">${{h.score}}/100</div>
                </div>
            `).join('');
        }} else if (scrLatest && (!d.latest || !d.latest.top_hits.length)) {{
            scrLatest.innerHTML = '<div style="color:#666;font-size:0.85rem;text-align:center;padding:1rem;">Belum ada screener run</div>';
        }}
    }} catch(e) {{}}
}}
refreshScreener();
setInterval(refreshScreener, 15000);
</script>
</body>
</html>""")

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
