#!/usr/bin/env python3
"""Daily Watchlist Digest — push to all users with active watchlists.

Runs every morning at 07:00 WIB (cron).
1. Scans all watchlist files in data/watchlists/
2. For each user, generates fresh digest (prices, sentiment)
3. Sends via Telegram DM if user has stocks in watchlist
4. Skips users with empty watchlists
"""

import asyncio
import glob
import json
import os
import sys
from datetime import datetime

# ─── Config ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import settings
from src.engine.watchlist import WatchlistEngine

import aiohttp

BOT_TOKEN = settings.bot_token
SEND_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
WATCHLIST_DIR = os.path.expanduser("~/idx-trading-bot/data/watchlists")

DRY_RUN = "--dry" in sys.argv


async def send_telegram(user_id: int, text: str) -> bool:
    """Send message to a specific Telegram user."""
    payload = {
        "chat_id": user_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(SEND_URL, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.json()
            return data.get("ok", False)


async def main():
    # Find all watchlist files
    pattern = os.path.join(WATCHLIST_DIR, "watchlist_*.json")
    files = glob.glob(pattern)

    if not files:
        print("[WatchlistDigest] No watchlist files found. Skipping.")
        return

    engine = WatchlistEngine()
    now = datetime.now()
    sent_count = 0
    skip_count = 0
    fail_count = 0
    empty_count = 0

    print(f"[WatchlistDigest] {now.strftime('%H:%M WIB')} — Processing {len(files)} watchlist file(s)")

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            user_id = int(filename.replace("watchlist_", "").replace(".json", ""))
        except ValueError:
            print(f"  SKIP: bad filename {filename}")
            skip_count += 1
            continue

        # Load entries
        try:
            with open(filepath) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  FAIL: {user_id} — can't read: {e}")
            fail_count += 1
            continue

        if not data:
            empty_count += 1
            continue  # empty watchlist, no digest to send

        # Generate fresh digest
        try:
            digest = await engine.generate_digest(user_id)
            text = engine.format_digest(digest)
        except Exception as e:
            print(f"  FAIL: {user_id} — digest error: {e}")
            fail_count += 1
            continue

        if DRY_RUN:
            print(f"  DRY: {user_id} ({len(data)} stocks) — would send digest")
            sent_count += 1
            continue

        # Send via Telegram
        ok = await send_telegram(user_id, text)
        if ok:
            symbol_list = ", ".join(
                e.get("symbol", "?") for e in (digest.entries or [])
            )
            print(f"  OK: {user_id} — {symbol_list}")
            sent_count += 1
        else:
            print(f"  FAIL: {user_id} — Telegram API rejected (blocked bot?)")
            fail_count += 1

    print(
        f"\n[WatchlistDigest] Done: {sent_count} sent, "
        f"{empty_count} empty, {fail_count} failed, {skip_count} skipped"
    )


if __name__ == "__main__":
    asyncio.run(main())
