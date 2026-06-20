#!/usr/bin/env python3
"""
IDX News Ingestion Pipeline Runner
===================================
Scrapes Indonesian financial news, classifies corporate events,
sends new event alerts to Telegram.

Usage:
    python scripts/run_ingestion.py           # live mode
    python scripts/run_ingestion.py --dry     # dry-run (no Telegram sends)
"""
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

# ── Setup ──────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.config import settings
from src.ingestion import scrape_all, classify_and_filter, format_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingestion-runner")

WIB = timezone(timedelta(hours=7))

BOT_TOKEN = settings.bot_token
ALERT_CHAT_ID = 157228659  # from .env ALERT_CHAT_ID
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

DRY_RUN = "--dry" in sys.argv


# ── Telegram Sender ────────────────────────────────────────

async def send_telegram(chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
    """Send message via Telegram Bot API."""
    if DRY_RUN:
        logger.info(f"[DRY-RUN] Would send to {chat_id}:\n{text[:200]}...")
        return True
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
            )
            result = resp.json()
            if not result.get("ok"):
                logger.error(f"Telegram send failed: {result}")
                return False
            return True
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False


# ── Main Pipeline ──────────────────────────────────────────

async def run_pipeline():
    """Scrape → Classify → Filter → Alert."""
    now = datetime.now(WIB)
    logger.info(f"=== IDX News Ingestion Pipeline — {now.strftime('%Y-%m-%d %H:%M WIB')} ===")
    if DRY_RUN:
        logger.info("[DRY-RUN MODE — no Telegram messages will be sent]")

    # Step 1: Scrape all sources
    logger.info("Step 1: Scraping news sources (Kontan, Bisnis, CNBC)...")
    articles = scrape_all()
    logger.info(f"  Scraped {len(articles)} articles total")

    if not articles:
        logger.warning("No articles scraped — sources may be down or blocked")
        summary = (
            f"📭 *IDX News Ingestion — {now.strftime('%d %b %Y %H:%M WIB')}*\n\n"
            f"Scraped: 0 articles\n"
            f"New events: 0\n\n"
            f"_No articles returned. Sources may be rate-limited or HTML structure changed._"
        )
        await send_telegram(ALERT_CHAT_ID, summary)
        return {"scraped": 0, "new_events": 0, "alerts_sent": 0}

    # Step 2: Classify and filter for relevant corporate events
    logger.info("Step 2: Classifying articles and filtering for corporate events...")
    new_events = classify_and_filter(articles)
    logger.info(f"  Found {len(new_events)} new corporate events")

    # Step 3: Send alerts for each new event
    alerts_sent = 0
    for i, event in enumerate(new_events, 1):
        alert_text = format_alert(event)
        cls = event.get("classification", {})
        logger.info(
            f"  Alert {i}/{len(new_events)}: {cls.get('event', 'Unknown')} "
            f"(conf={cls.get('confidence', 0):.0f}%) — {event['title'][:60]}"
        )
        success = await send_telegram(ALERT_CHAT_ID, alert_text)
        if success:
            alerts_sent += 1
        # Rate limit: 200ms between sends
        if i < len(new_events):
            await asyncio.sleep(0.2)

    # Step 4: Summary
    summary_lines = [
        f"📊 *IDX News Ingestion — {now.strftime('%d %b %Y %H:%M WIB')}*",
        "",
        f"├ Scraped: {len(articles)} articles (Kontan + Bisnis + CNBC)",
        f"├ New events: {len(new_events)}",
        f"├ Alerts sent: {alerts_sent}/{len(new_events) if new_events else 0}",
        f"└ Previously seen: {len(classify_and_filter.__module__ and [])} (deduped)",
    ]

    if new_events:
        event_types = {}
        for ev in new_events:
            etype = ev.get("classification", {}).get("event", "Unknown")
            event_types[etype] = event_types.get(etype, 0) + 1
        summary_lines.append("")
        summary_lines.append("*Event breakdown:*")
        for etype, count in sorted(event_types.items(), key=lambda x: -x[1]):
            summary_lines.append(f"  • {etype}: {count}")

    summary = "\n".join(summary_lines)
    logger.info("Step 4: Sending summary to channel...")
    await send_telegram(ALERT_CHAT_ID, summary)

    # Print final report
    report = {
        "scraped": len(articles),
        "new_events": len(new_events),
        "alerts_sent": alerts_sent,
        "events": [
            {
                "title": ev["title"][:80],
                "event": ev.get("classification", {}).get("event", "Unknown"),
                "confidence": ev.get("classification", {}).get("confidence", 0),
                "source": ev["source"],
            }
            for ev in new_events
        ],
    }

    logger.info("=== Pipeline Complete ===")
    logger.info(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    result = asyncio.run(run_pipeline())
    print(json.dumps(result, indent=2, ensure_ascii=False))
