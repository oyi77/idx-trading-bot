#!/usr/bin/env python3
"""SATPAM 0858 (Kakriput act_435670549443081) — patrol cron."""
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

ACT_ID = "435670549443081"
API_VER = "v22.0"
API_BASE = f"https://graph.facebook.com/{API_VER}"

def load_token():
    path = "/home/openclaw/projects/1ai-ads/.env"
    for line in open(path).read().splitlines():
        if not line or line.startswith("#"):
            continue
        if line.split("=", 1)[0] == "META_ACCESS_TOKEN":
            return line.split("=", 1)[1].strip()
    raise RuntimeError("META_ACCESS_TOKEN not found in .env")

TOKEN = load_token()

TOKEN = load_token()

def fb_get(endpoint, params=None):
    url = f"{API_BASE}/{endpoint}"
    if params:
        qs = urllib.parse.urlencode(params)
        url = f"{url}?{qs}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def fb_post(endpoint, data):
    url = f"{API_BASE}/{endpoint}"
    qs = urllib.parse.urlencode(data)
    req = urllib.request.Request(url, data=qs.encode(), method="POST")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def main():
    now = datetime.now()
    since = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    until = now.strftime("%Y-%m-%d")

    print(f"🛡️ SATPAM 0858 | {now.strftime('%Y-%m-%d %H:%M')} WIB")

    # 1. Token/account verification
    try:
        acc = fb_get(f"act_{ACT_ID}", {"fields": "name"})
        print(f"✅ Token valid | Account: {acc.get('name', ACT_ID)}")
    except Exception as e:
        print(f"❌ Token/account check failed: {e}")
        return

    # 2. Fetch all campaigns
    all_campaigns = []
    nxt = f"act_{ACT_ID}/campaigns?fields=id,name,status,daily_budget,spend,cpc&limit=200"
    while nxt:
        res = fb_get(nxt)
        all_campaigns.extend(res.get("data", []))
        nxt = res.get("paging", {}).get("next")
        if nxt:
            time.sleep(0.6)

    print(f"📋 Campaigns loaded: {len(all_campaigns)}")

    # 3. Fetch 7-day insights
    insights = {}
    nxt = (f"act_{ACT_ID}/insights"
           f"?fields=campaign_id,campaign_name,spend,cpc,clicks,ctr,impressions"
           f"&level=campaign&time_range={json.dumps({'since':since,'until':until})}"
           f"&limit=200")
    while nxt:
        res = fb_get(nxt)
        for row in res.get("data", []):
            cid = row.get("campaign_id")
            if cid:
                insights[cid] = row
        nxt = res.get("paging", {}).get("next")
        if nxt:
            time.sleep(1.5)

    print(f"📊 Insights rows: {len(insights)}")

    # 4. Compute global CPC
    total_spend = 0.0
    total_clicks = 0
    for c in all_campaigns:
        if c.get("status") != "ACTIVE":
            continue
        ins = insights.get(c["id"], {})
        sp = float(ins.get("spend", 0) or 0)
        cl = int(ins.get("clicks", 0) or 0)
        total_spend += sp
        total_clicks += cl

    global_cpc = total_spend / total_clicks if total_clicks > 0 else 0.0
    mode = "AMAN" if global_cpc < 120 else "NORMAL"
    print(f"💰 Global CPC: Rp{global_cpc:,.0f} | Mode: {mode}")

    # 5. Classify campaigns
    # Build lookup for insights by campaign id
    monsters = []
    watch = []
    winners = []
    auto_on = []
    lc_eligible = []
    off_count = 0
    active_count = 0

    for c in all_campaigns:
        name = c.get("name", "")
        status = c.get("status", "")
        cid = c.get("id", "")
        ins = insights.get(cid, {})
        spend = float(ins.get("spend", 0) or 0)
        cpc = float(ins.get("cpc", 0) or 0)
        clicks = int(ins.get("clicks", 0) or 0)
        ctr = float(ins.get("ctr", 0) or 0)

        if status == "ACTIVE":
            active_count += 1
        if name.startswith("OFF_") or name.startswith("DEAD_"):
            off_count += 1

        # MONSTER (always active)
        if cpc >= 500 and spend > 1000:
            monsters.append({"name": name, "cpc": cpc, "spend": spend})
        elif cpc > 200 and clicks == 0 and spend > 500:
            monsters.append({"name": name, "cpc": cpc, "spend": spend})

        # WATCH
        if cpc > 200 and clicks > 0 and spend > 2000:
            watch.append({"name": name, "cpc": cpc, "spend": spend})

        # WINNER
        if cpc < 120 and clicks > 5 and spend > 10000:
            winners.append({"name": name, "cpc": cpc, "spend": spend,
                            "clicks": clicks, "ctr": ctr})

        # AUTO-ON (paused non-OFF_)
        if status == "PAUSED" and not name.startswith("OFF_") and not name.startswith("DEAD_"):
            if cpc < 200 and clicks > 3 and spend > 2000:
                auto_on.append({"name": name, "cpc": cpc, "spend": spend,
                                "clicks": clicks})

        # LC eligible
        if "LC" in name.upper() and cpc < 120 and status == "ACTIVE":
            lc_eligible.append({"name": name, "cpc": cpc, "spend": spend})

    # 6. Execute actions in NORMAL mode only
    renamed_winners = 0
    auto_on_count = 0
    paused_monsters = 0

    if mode == "NORMAL":
        # MONSTER: pause (and rename OFF_ for first subtype)
        for m in monsters:
            name = m["name"]
            cid = None
            for c in all_campaigns:
                if c["name"] == name:
                    cid = c["id"]
                    break
            if not cid:
                continue
            try:
                fb_post(cid, {"status": "PAUSED"})
                time.sleep(1.5)
                if m["cpc"] >= 500:
                    # Rename to OFF_
                    new_name = f"OFF_{name}"
                    fb_post(cid, {"name": new_name})
                    time.sleep(0.7)
                paused_monsters += 1
            except Exception as e:
                print(f"❌ Failed to pause {name}: {e}")

        # WINNER: rename to 🌟_
        for w in winners:
            name = w["name"]
            if name.startswith("🌟_"):
                continue
            cid = None
            for c in all_campaigns:
                if c["name"] == name:
                    cid = c["id"]
                    break
            if not cid:
                continue
            try:
                fb_post(cid, {"name": f"🌟_{name}"})
                time.sleep(0.7)
                renamed_winners += 1
            except Exception as e:
                print(f"❌ Failed to star {name}: {e}")

        # AUTO-ON: reactivate
        for a in auto_on:
            name = a["name"]
            cid = None
            for c in all_campaigns:
                if c["name"] == name:
                    cid = c["id"]
                    break
            if not cid:
                continue
            try:
                fb_post(cid, {"status": "ACTIVE"})
                time.sleep(1.5)
                auto_on_count += 1
            except Exception as e:
                print(f"❌ Failed to activate {name}: {e}")
    else:
        # AMAN mode: no mutations
        print("🔒 MODE AMAN — no mutations performed")

    # 7. Meta rules check
    rules = []
    try:
        rules_res = fb_get(f"act_{ACT_ID}/adrules_library",
                           {"fields": "id,name,execution_spec", "limit": 50})
        rules = rules_res.get("data", [])
        pause_rules = [r for r in rules if "pause" in r.get("name", "").lower()
                       or "stop" in r.get("name", "").lower()
                       or "spent" in r.get("name", "").lower()]
    except Exception:
        pause_rules = []

    # 8. Report
    print("\n" + "="*60)
    print(f"🛡️ SATPAM 0858 | {now.strftime('%Y-%m-%d %H:%M')} WIB")
    print(f"ACTIVE: {active_count} | Global CPC: Rp{global_cpc:,.0f} | Mode: {mode}")
    print(f"OFF_: {off_count}")
    print(f"{'='*60}")

    print(f"\n💀 MONSTER: {len(monsters)} campaign(s)")
    if monsters:
        for m in monsters:
            print(f"   • {m['name']} | CPC: Rp{m['cpc']:,.0f} | Spend: Rp{m['spend']:,.0f}")
    else:
        print("   —")

    print(f"\n👀 WATCH: {len(watch)} campaign(s)")
    if watch:
        for w in watch:
            print(f"   • {w['name']} | CPC: Rp{w['cpc']:,.0f} | Spend: Rp{w['spend']:,.0f}")
    else:
        print("   —")

    print(f"\n🌟 WINNER: {len(winners)} campaign(s) | renamed: {renamed_winners}")
    if winners:
        for w in winners:
            print(f"   • {w['name']} | CPC: Rp{w['cpc']:,.0f} | Spend: Rp{w['spend']:,.0f} | "
                  f"Clicks: {w['clicks']} | CTR: {w['ctr']:.2f}%")
    else:
        print("   —")

    print(f"\n✅ AUTO-ON: {auto_on_count} activated")
    if auto_on:
        for a in auto_on:
            print(f"   • {a['name']} | CPC: Rp{a['cpc']:,.0f} | Spend: Rp{a['spend']:,.0f} | Clicks: {a['clicks']}")
    else:
        print("   —")

    print(f"\n💰 LC eligible: {len(lc_eligible)} campaign(s)")
    if lc_eligible:
        for lc in lc_eligible:
            print(f"   • {lc['name']} | CPC: Rp{lc['cpc']:,.0f} | Spend: Rp{lc['spend']:,.0f}")
    else:
        print("   —")

    print(f"\n⚠️ Meta rules: {len(rules)} total | {len(pause_rules)} pause-type")
    if pause_rules:
        for r in pause_rules:
            print(f"   • {r['name']} (id: {r['id']})")
    else:
        print("   —")

    print("\n" + "="*60)
    print("Patrol complete.")

if __name__ == "__main__":
    main()
