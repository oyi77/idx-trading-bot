"""
Admin Dashboard — Full system monitoring for IDX Trading Bot.
Password-protected. Real-time data. All metrics.
"""
from datetime import datetime, timedelta
from typing import Optional
import json
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "openclaw")
SESSION_COOKIE = "admin_session"
SESSION_SECRET=os.environ.get("SESSION_SECRET", "vilona-saham-admin-2026")


def _check_auth(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE, "")
    if not token:
        return False
    import hashlib
    expected = hashlib.sha256(f"{ADMIN_PASSWORD}:{SESSION_SECRET}".encode()).hexdigest()
    return token == expected


def _create_token() -> str:
    import hashlib
    return hashlib.sha256(f"{ADMIN_PASSWORD}:{SESSION_SECRET}".encode()).hexdigest()


def register_admin_routes(app: FastAPI):
    @app.get("/admin/login", response_class=HTMLResponse)
    async def admin_login_page(request: Request):
        if _check_auth(request):
            return RedirectResponse(url="/dashboard", status_code=302)
        return HTMLResponse(_LOGIN_HTML)

    @app.post("/admin/login")
    async def admin_login(request: Request):
        form = await request.form()
        password = form.get("password", "")
        if password == ADMIN_PASSWORD:
            token = _create_token()
            response = RedirectResponse(url="/dashboard", status_code=302)
            response.set_cookie(key=SESSION_COOKIE, value=token, httponly=True, max_age=86400)
            return response
        return HTMLResponse(_LOGIN_HTML.replace("<!-- ERROR -->", '<div class="error">Password salah!</div>'))

    @app.get("/admin/logout")
    async def admin_logout():
        response = RedirectResponse(url="/admin/login", status_code=302)
        response.delete_cookie(SESSION_COOKIE)
        return response

    @app.get("/api/admin/data")
    async def admin_data(request: Request):
        if not _check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return JSONResponse(await _get_all_data())

    @app.get("/api/admin/users")
    async def admin_users(request: Request):
        if not _check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return JSONResponse(await _get_users_data())

    @app.get("/api/admin/backtest")
    async def admin_backtest(request: Request):
        if not _check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return JSONResponse(await _get_backtest_data())

    @app.get("/api/admin/activity")
    async def admin_activity(request: Request):
        if not _check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return JSONResponse(await _get_activity_data())

    @app.get("/api/admin/errors")
    async def admin_errors(request: Request):
        if not _check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return JSONResponse(await _get_error_data())

    @app.get("/dashboard", response_class=HTMLResponse)
    async def admin_dashboard(request: Request):
        if not _check_auth(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        return HTMLResponse(_DASHBOARD_HTML)


async def _get_all_data() -> dict:
    from sqlalchemy import create_engine, func
    from sqlalchemy.orm import sessionmaker
    from src.models import User, Subscription, AnalysisJournal, Alert, TradePlan
    from src.config import settings

    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    data = {}
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    with Session() as session:
        data["total_users"] = session.query(func.count(User.id)).scalar() or 0
        data["new_today"] = session.query(func.count(User.id)).filter(User.created_at >= today).scalar() or 0
        data["new_week"] = session.query(func.count(User.id)).filter(User.created_at >= week_start).scalar() or 0
        data["new_month"] = session.query(func.count(User.id)).filter(User.created_at >= month_start).scalar() or 0

        subs = dict(session.query(Subscription.tier, func.count(Subscription.id)).group_by(Subscription.tier).all())
        data["subscriptions"] = {
            "free": subs.get("free", 0), "pro": subs.get("pro", 0),
            "premium": subs.get("premium", 0), "lifetime": subs.get("lifetime", 0),
            "whitelabel": subs.get("whitelabel", 0),
        }
        data["paid_users"] = sum(v for k, v in data["subscriptions"].items() if k != "free")
        data["mrr"] = data["subscriptions"]["pro"] * 79900 + data["subscriptions"]["premium"] * 149900

        expiring = session.query(Subscription).filter(
            Subscription.end_date.isnot(None),
            Subscription.end_date >= now,
            Subscription.end_date <= now + timedelta(days=7),
        ).all()
        data["expiring_soon"] = [
            {"user_id": getattr(s, 'user_id', None), "tier": s.tier,
             "end_date": s.end_date.strftime("%Y-%m-%d") if s.end_date else None}
            for s in expiring
        ]

        data["total_analyses"] = session.query(func.count(AnalysisJournal.id)).scalar() or 0
        data["analyses_today"] = session.query(func.count(AnalysisJournal.id)).filter(AnalysisJournal.timestamp >= today).scalar() or 0
        data["analyses_week"] = session.query(func.count(AnalysisJournal.id)).filter(AnalysisJournal.timestamp >= week_start).scalar() or 0

        resolved = session.query(func.count(AnalysisJournal.id)).filter(AnalysisJournal.resolved == True).scalar() or 0
        accurate = session.query(func.count(AnalysisJournal.id)).filter(AnalysisJournal.resolved == True, AnalysisJournal.accuracy_pct > 0).scalar() or 0
        data["win_rate"] = round(accurate / resolved * 100, 1) if resolved > 0 else 0
        data["total_resolved"] = resolved
        data["total_accurate"] = accurate

        data["active_alerts"] = session.query(func.count(Alert.id)).filter(Alert.is_active == True, Alert.is_triggered == False).scalar() or 0
        data["triggered_alerts"] = session.query(func.count(Alert.id)).filter(Alert.is_triggered == True).scalar() or 0
        data["active_plans"] = session.query(func.count(TradePlan.id)).filter(TradePlan.status == "active").scalar() or 0

        recent = session.query(AnalysisJournal).order_by(AnalysisJournal.timestamp.desc()).limit(20).all()
        data["recent_activity"] = [
            {"symbol": r.symbol, "signal": r.signal, "score": r.score,
             "timestamp": r.timestamp.strftime("%H:%M") if r.timestamp else None}
            for r in recent
        ]

    data["bot_health"] = _get_bot_health()
    data["backtest"] = _get_backtest_results()
    data["autopilot"] = _get_autopilot_status()
    data["timestamp"] = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    return data


async def _get_users_data() -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models import User, Subscription
    from src.config import settings

    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    users = []
    with Session() as session:
        for u in session.query(User).order_by(User.created_at.desc()).limit(100).all():
            sub = session.query(Subscription).filter_by(user_id=u.id).first()
            users.append({
                "id": u.telegram_id, "username": u.username or "", "full_name": u.full_name or "",
                "tier": sub.tier if sub else "free", "activity": u.activity_count or 0,
                "last_active": u.last_active.strftime("%Y-%m-%d %H:%M") if u.last_active else None,
                "created": u.created_at.strftime("%Y-%m-%d") if u.created_at else None,
                "sub_end": sub.end_date.strftime("%Y-%m-%d") if sub and sub.end_date else None,
                "followup_stage": u.followup_stage or 0,
            })
    return {"users": users, "total": len(users)}


async def _get_backtest_data() -> dict:
    return {"backtest": _get_backtest_results()}


async def _get_activity_data() -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models import AnalysisJournal
    from src.config import settings

    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    activities = []
    with Session() as session:
        for r in session.query(AnalysisJournal).order_by(AnalysisJournal.timestamp.desc()).limit(50).all():
            activities.append({
                "symbol": r.symbol, "signal": r.signal, "score": r.score,
                "accuracy": r.accuracy_pct, "resolved": r.resolved,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M") if r.timestamp else None,
            })
    return {"activities": activities}


async def _get_error_data() -> dict:
    errors = []
    log_files = [str(PROJECT_ROOT / "data" / "bot.log"), "/tmp/idx-bot.log"]
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                with open(log_file, "r") as f:
                    for line in f.readlines()[-50:]:
                        if "ERROR" in line or "WARNING" in line or "Traceback" in line:
                            errors.append(line.strip()[:200])
            except Exception:
                pass
    return {"errors": errors[-20:]}


def _get_bot_health() -> dict:
    try:
        result = subprocess.run(["pgrep", "-f", "python3 src/main.py"], capture_output=True, text=True)
        pids = [p for p in result.stdout.strip().split("\n") if p.strip()]
        if pids:
            mem = subprocess.run(["ps", "-o", "pid,rss,pcpu,etime", "-p", pids[-1]], capture_output=True, text=True)
            lines = mem.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                return {
                    "status": "running",
                    "pid": int(parts[0]) if parts[0].isdigit() else 0,
                    "memory_mb": round(int(parts[1]) / 1024, 1) if len(parts) > 1 and parts[1].isdigit() else 0,
                    "cpu_pct": parts[2] if len(parts) > 2 else "0",
                    "uptime": parts[3] if len(parts) > 3 else "unknown",
                }
        return {"status": "stopped", "pid": 0, "memory_mb": 0, "cpu_pct": "0", "uptime": "N/A"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _get_backtest_results() -> dict:
    results_dir = PROJECT_ROOT / "data" / "backtest_results"
    if not results_dir.exists():
        return {"swing": None, "scalp": None}
    result = {"swing": None, "scalp": None}
    for key in ("swing", "scalp"):
        files = sorted(results_dir.glob(f"{key}_*.json"), reverse=True)
        if files:
            try:
                with open(files[0]) as f:
                    result[key] = json.load(f)
            except Exception:
                pass
    return result


def _get_autopilot_status() -> dict:
    status_file = PROJECT_ROOT / "data" / "autopilot" / "status.json"
    if status_file.exists():
        try:
            with open(status_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_LOGIN_HTML = """<!DOCTYPE html>
<html lang="id"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login — Vilona Saham</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',system-ui,sans-serif;background:#000;color:#f1f5f9;display:flex;align-items:center;justify-content:center;min-height:100vh}
.login-box{background:rgba(10,10,20,.8);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.06);border-radius:20px;padding:48px;max-width:400px;width:90%;text-align:center}
h1{font-size:24px;font-weight:800;margin-bottom:8px}
h1 span{background:linear-gradient(135deg,#00e5ff,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
p{color:#94a3b8;font-size:14px;margin-bottom:32px}
input[type=password]{width:100%;padding:14px 18px;border-radius:12px;border:1px solid rgba(255,255,255,.1);background:rgba(0,0,0,.4);color:#f1f5f9;font-size:16px;outline:none;margin-bottom:16px}
input[type=password]:focus{border-color:#00e5ff}
button{width:100%;padding:14px;border-radius:12px;border:none;background:linear-gradient(135deg,#00e5ff,#0097a7);color:#000;font-size:16px;font-weight:700;cursor:pointer;transition:all .3s}
button:hover{transform:translateY(-2px);box-shadow:0 0 30px rgba(0,229,255,.3)}
.error{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);color:#ef4444;padding:10px;border-radius:8px;margin-bottom:16px;font-size:13px}
</style></head><body>
<div class="login-box">
<h1>⚡ <span>Vilona Saham</span></h1><p>Admin Dashboard Login</p><!-- ERROR -->
<form method="POST" action="/admin/login">
<input type="password" name="password" placeholder="Password" autofocus required>
<button type="submit">Masuk →</button>
</form></div></body></html>"""


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="id"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Dashboard — Vilona Saham</title>
<style>
:root{--bg:#000;--cyan:#00e5ff;--purple:#a855f7;--amber:#f59e0b;--green:#10b981;--red:#ef4444;--glass:rgba(10,10,20,.7);--border:rgba(255,255,255,.06);--text:#f1f5f9;--dim:#94a3b8}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:#000}::-webkit-scrollbar-thumb{background:var(--cyan);border-radius:2px}
.topbar{position:sticky;top:0;z-index:100;padding:12px 24px;background:rgba(0,0,0,.85);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.topbar h1{font-size:18px;font-weight:800}h1 span{background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block}.dot.green{background:var(--green);box-shadow:0 0 8px var(--green)}.dot.red{background:var(--red)}
.topbar a{color:var(--dim);text-decoration:none;font-size:13px}.topbar a:hover{color:var(--cyan)}
.container{max-width:1400px;margin:0 auto;padding:24px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:24px}
.stat{padding:24px;border-radius:16px;background:var(--glass);border:1px solid var(--border);transition:all .3s}.stat:hover{border-color:rgba(0,229,255,.2)}
.stat .num{font-family:'JetBrains Mono',monospace;font-size:32px;font-weight:900;background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stat .label{font-size:12px;color:var(--dim);margin-top:4px;font-weight:600;letter-spacing:.5px;text-transform:uppercase}
.stat .sub{font-size:11px;color:var(--dim);margin-top:2px}
.card{padding:24px;border-radius:16px;background:var(--glass);border:1px solid var(--border);margin-bottom:24px}
.card h2{font-size:16px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.card h2 .badge{font-size:11px;padding:3px 10px;border-radius:8px;font-weight:600}
.badge.green{background:rgba(16,185,129,.15);color:var(--green)}.badge.red{background:rgba(239,68,68,.15);color:var(--red)}
.badge.amber{background:rgba(245,158,11,.15);color:var(--amber)}.badge.cyan{background:rgba(0,229,255,.15);color:var(--cyan)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 12px;border-bottom:1px solid var(--border);color:var(--dim);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.5px}
td{padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.03)}tr:hover td{background:rgba(0,229,255,.02)}
.tier{padding:3px 10px;border-radius:6px;font-size:11px;font-weight:700}
.tier.free{background:rgba(148,163,184,.15);color:#94a3b8}.tier.pro{background:rgba(0,229,255,.15);color:var(--cyan)}
.tier.premium{background:rgba(168,85,247,.15);color:var(--purple)}.tier.lifetime{background:rgba(245,158,11,.15);color:var(--amber)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:24px}@media(max-width:768px){.grid2{grid-template-columns:1fr}}
.health{display:flex;gap:16px;flex-wrap:wrap}
.health-item{padding:12px 20px;border-radius:10px;background:rgba(0,0,0,.3);border:1px solid var(--border);min-width:120px}
.health-item .val{font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700}
.refresh-bar{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--dim)}.refresh-bar .timer{color:var(--cyan);font-family:'JetBrains Mono',monospace}
</style></head><body>
<div class="topbar">
<h1>⚡ <span>Vilona Saham</span> — Admin</h1>
<div class="status"><div class="refresh-bar">Auto-refresh: <span class="timer" id="timer">30s</span></div>
<span id="health-dot" class="dot green"></span><span id="health-text">Checking...</span><a href="/admin/logout">Logout</a></div></div>
<div class="container">
<div class="stats">
<div class="stat"><div class="num" id="total-users">—</div><div class="label">Total Users</div><div class="sub" id="new-today">— new today</div></div>
<div class="stat"><div class="num" id="paid-users">—</div><div class="label">Paid Users</div><div class="sub" id="paid-breakdown">—</div></div>
<div class="stat"><div class="num" id="mrr">—</div><div class="label">MRR</div><div class="sub">Monthly Recurring</div></div>
<div class="stat"><div class="num" id="win-rate">—</div><div class="label">Win Rate</div><div class="sub" id="win-detail">— resolved</div></div>
<div class="stat"><div class="num" id="analyses-today">—</div><div class="label">Analyses Today</div><div class="sub" id="analyses-week">— this week</div></div>
<div class="stat"><div class="num" id="active-alerts">—</div><div class="label">Active Alerts</div><div class="sub" id="triggered-alerts">— triggered</div></div></div>
<div class="card"><h2>🤖 Bot Health</h2><div class="health">
<div class="health-item"><div class="val" id="h-status">—</div><div class="sub">Status</div></div>
<div class="health-item"><div class="val" id="h-pid">—</div><div class="sub">PID</div></div>
<div class="health-item"><div class="val" id="h-memory">—</div><div class="sub">Memory</div></div>
<div class="health-item"><div class="val" id="h-cpu">—</div><div class="sub">CPU</div></div>
<div class="health-item"><div class="val" id="h-uptime">—</div><div class="sub">Uptime</div></div></div></div>
<div class="grid2"><div class="card"><h2>💎 Subscriptions</h2><table>
<tr><th>Tier</th><th>Users</th><th>Revenue</th></tr>
<tr><td><span class="tier free">Free</span></td><td id="sub-free">—</td><td>Rp0</td></tr>
<tr><td><span class="tier pro">Pro</span></td><td id="sub-pro">—</td><td id="rev-pro">—</td></tr>
<tr><td><span class="tier premium">Premium</span></td><td id="sub-premium">—</td><td id="rev-premium">—</td></tr>
<tr><td><span class="tier lifetime">Lifetime</span></td><td id="sub-lifetime">—</td><td id="rev-lifetime">—</td></tr></table></div>
<div class="card"><h2>⏰ Expiring Soon <span class="badge amber">7 days</span></h2>
<div id="expiring-list"><p style="color:var(--dim);font-size:13px">Loading...</p></div></div></div>
<div class="card"><h2>📊 Backtest Results <span class="badge cyan">Weekly</span></h2><div class="grid2">
<div><h3 style="font-size:14px;margin-bottom:12px;color:var(--purple)">📈 Swing Trade</h3><div id="bt-swing"><p style="color:var(--dim)">Loading...</p></div></div>
<div><h3 style="font-size:14px;margin-bottom:12px;color:var(--amber)">⚡ Scalping</h3><div id="bt-scalp"><p style="color:var(--dim)">Loading...</p></div></div></div></div>
<div class="card"><h2>🤖 Autopilot Status</h2><div class="health">
<div class="health-item"><div class="val" id="ap-daily">—</div><div class="sub">Last Daily</div></div>
<div class="health-item"><div class="val" id="ap-backtest">—</div><div class="sub">Last Backtest</div></div>
<div class="health-item"><div class="val" id="ap-followup">—</div><div class="sub">Last Follow-up</div></div>
<div class="health-item"><div class="val" id="ap-signals">—</div><div class="sub">Signals Posted</div></div>
<div class="health-item"><div class="val" id="ap-followups">—</div><div class="sub">Follow-ups Sent</div></div></div></div>
<div class="card"><h2>👥 Users <span class="badge green" id="user-count">—</span></h2><div style="overflow-x:auto"><table>
<tr><th>ID</th><th>Name</th><th>Username</th><th>Tier</th><th>Activity</th><th>Last Active</th><th>Sub End</th><th>Follow-up</th></tr>
<tbody id="user-table"><tr><td colspan="8" style="color:var(--dim)">Loading...</td></tr></tbody></table></div></div>
<div class="card"><h2>📡 Recent Activity</h2><div style="overflow-x:auto"><table>
<tr><th>Time</th><th>Symbol</th><th>Signal</th><th>Score</th><th>Accuracy</th><th>Resolved</th></tr>
<tbody id="activity-table"><tr><td colspan="6" style="color:var(--dim)">Loading...</td></tr></tbody></table></div></div>
<div class="card"><h2>🚨 Error Log <span class="badge red" id="error-count">0</span></h2>
<div id="error-list" style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--dim);max-height:300px;overflow-y:auto"><p>No errors</p></div></div>
<div style="text-align:center;padding:20px;font-size:12px;color:var(--dim)">Last updated: <span id="last-updated">—</span> · Auto-refresh 30s</div></div>
<script>
async function loadData(){try{const r=await fetch('/api/admin/data');if(r.status===401){window.location='/admin/login';return}const d=await r.json();
document.getElementById('total-users').textContent=d.total_users;document.getElementById('new-today').textContent='+'+d.new_today+' today';
document.getElementById('paid-users').textContent=d.paid_users;document.getElementById('paid-breakdown').textContent='Pro:'+(d.subscriptions?.pro||0)+' Prem:'+(d.subscriptions?.premium||0)+' Life:'+(d.subscriptions?.lifetime||0);
document.getElementById('mrr').textContent='Rp'+(d.mrr||0).toLocaleString('id');document.getElementById('win-rate').textContent=d.win_rate+'%';
document.getElementById('win-detail').textContent=d.total_accurate+'/'+d.total_resolved+' resolved';document.getElementById('analyses-today').textContent=d.analyses_today;
document.getElementById('analyses-week').textContent=d.analyses_week+' this week';document.getElementById('active-alerts').textContent=d.active_alerts;
document.getElementById('triggered-alerts').textContent=d.triggered_alerts+' triggered';
const h=d.bot_health||{};document.getElementById('h-status').textContent=h.status||'?';document.getElementById('h-pid').textContent=h.pid||'—';
document.getElementById('h-memory').textContent=h.memory_mb?h.memory_mb+'MB':'—';document.getElementById('h-cpu').textContent=h.cpu_pct||'—';
document.getElementById('h-uptime').textContent=h.uptime||'—';document.getElementById('health-dot').className='dot '+(h.status==='running'?'green':'red');
document.getElementById('health-text').textContent=h.status==='running'?'Online':'Offline';
const s=d.subscriptions||{};document.getElementById('sub-free').textContent=s.free||0;document.getElementById('sub-pro').textContent=s.pro||0;
document.getElementById('sub-premium').textContent=s.premium||0;document.getElementById('sub-lifetime').textContent=s.lifetime||0;
document.getElementById('rev-pro').textContent='Rp'+((s.pro||0)*79900).toLocaleString('id');document.getElementById('rev-premium').textContent='Rp'+((s.premium||0)*149900).toLocaleString('id');
document.getElementById('rev-lifetime').textContent='Rp'+((s.lifetime||0)*1999900).toLocaleString('id');
const exp=d.expiring_soon||[];document.getElementById('expiring-list').innerHTML=exp.length===0?'<p style="color:var(--dim);font-size:13px">Tidak ada expired 7 hari</p>'
:exp.map(e=>'<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:13px"><span class="tier '+e.tier+'">'+e.tier+'</span> · User #'+e.user_id+' · Exp: '+e.end_date+'</div>').join('');
const bt=d.backtest||{};['swing','scalp'].forEach(k=>{const el=document.getElementById('bt-'+k);const b=bt[k];
if(b){el.innerHTML='<div style="font-size:13px;line-height:2">Win Rate: <b style="color:var(--green)">'+b.win_rate+'%</b><br>Trades: '+b.total_trades+' (W:'+b.wins+' L:'+b.losses+')<br>Avg Return: '+b.avg_return_pct+'%<br>Best: +'+b.best_trade_pct+'% · Worst: '+b.worst_trade_pct+'%<br>Max DD: '+b.max_drawdown_pct+'% · R:R: '+b.avg_rr_achieved+'</div>'}else{el.innerHTML='<p style="color:var(--dim)">No data yet</p>'}});
const ap=d.autopilot||{};document.getElementById('ap-daily').textContent=ap.last_daily_run?new Date(ap.last_daily_run).toLocaleDateString('id'):'Never';
document.getElementById('ap-backtest').textContent=ap.last_weekly_backtest?new Date(ap.last_weekly_backtest).toLocaleDateString('id'):'Never';
document.getElementById('ap-followup').textContent=ap.last_followup_sweep?new Date(ap.last_followup_sweep).toLocaleDateString('id'):'Never';
document.getElementById('ap-signals').textContent=ap.total_signals_posted||0;document.getElementById('ap-followups').textContent=ap.total_followups_sent||0;
const acts=d.recent_activity||[];document.getElementById('activity-table').innerHTML=acts.length===0?'<tr><td colspan="6" style="color:var(--dim)">No activity</td></tr>'
:acts.map(a=>'<tr><td>'+(a.timestamp||'—')+'</td><td><b>'+a.symbol+'</b></td><td>'+(a.signal||'—')+'</td><td>'+(a.score||'—')+'</td><td>'+(a.accuracy||'—')+'</td><td>'+(a.accuracy!=null?'✅':'⏳')+'</td></tr>').join('');
document.getElementById('last-updated').textContent=d.timestamp||new Date().toISOString()}catch(e){console.error(e)}}
async function loadUsers(){try{const r=await fetch('/api/admin/users');if(r.status!==200)return;const d=await r.json();
document.getElementById('user-count').textContent=d.total;const u=d.users||[];
document.getElementById('user-table').innerHTML=u.length===0?'<tr><td colspan="8" style="color:var(--dim)">No users</td></tr>'
:u.map(x=>'<tr><td>'+x.id+'</td><td>'+x.full_name+'</td><td>@'+x.username+'</td><td><span class="tier '+x.tier+'">'+x.tier+'</span></td><td>'+x.activity+'</td><td>'+(x.last_active||'—')+'</td><td>'+(x.sub_end||'—')+'</td><td>Stage '+x.followup_stage+'</td></tr>').join('')}catch(e){}}
async function loadErrors(){try{const r=await fetch('/api/admin/errors');if(r.status!==200)return;const d=await r.json();
const e=d.errors||[];document.getElementById('error-count').textContent=e.length;
document.getElementById('error-list').innerHTML=e.length===0?'<p style="color:var(--green)">✅ No errors</p>'
:e.map(x=>'<div style="padding:6px 0;border-bottom:1px solid var(--border);word-break:break-all">'+x+'</div>').join('')}catch(e){}}
let cd=30;function tick(){cd--;document.getElementById('timer').textContent=cd+'s';if(cd<=0){cd=30;loadData();loadUsers();loadErrors()}}
loadData();loadUsers();loadErrors();setInterval(tick,1000);
</script></body></html>"""
