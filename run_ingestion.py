#!/usr/bin/env python3
"""Run the IDX news ingestion pipeline and send alerts to Telegram."""
import sys
import os
import json
import asyncio
import logging

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from src.ingestion import scrape_all, classify_and_filter, format_alert


async def send_telegram_alerts(bot_token: str, chat_id: str, alerts: list[str]):
    """Send formatted alerts to Telegram via bot API."""
    import urllib.request

    for alert_text in alerts:
        payload = json.dumps({
            "chat_id": chat_id,
            "text": alert_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }).encode()

        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read())
            if result.get("ok"):
                logger.info(f"Alert sent OK: {alert_text[:60]}...")
            else:
                logger.warning(f"Telegram API error: {result}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")


async def main():
    # Load bot token from .env
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path, override=True)

    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        print("ERROR: BOT_TOKEN not set in .env")
        sys.exit(1)

    # Try to find a channel/group chat_id from env or use a default
    chat_id = os.environ.get("ALERT_CHAT_ID", "")
    if not chat_id:
        # Try common env var names
        for key in ["TELEGRAM_CHAT_ID", "CHANNEL_ID", "GROUP_CHAT_ID", "ADMIN_CHAT_ID"]:
            val = os.environ.get(key, "")
            if val:
                chat_id = val
                break

    print(f"=" * 60)
    print(f"IDX News Ingestion Pipeline")
    print(f"=" * 60)

    # Step 1: Scrape all sources
    print(f"\n[1/4] Scraping news sources (Kontan, Bisnis, CNBC)...")
    articles = scrape_all()
    print(f"  → Scraped {len(articles)} total articles")

    # Breakdown by source
    source_counts = {}
    for a in articles:
        src = a["source"]
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, cnt in sorted(source_counts.items()):
        print(f"    {src}: {cnt} articles")

    if not articles:
        print("\n  No articles found. All sources may be down or returning empty.")
        print("  Summary: 0 scraped, 0 new events")
        return

    # Step 2: Classify and filter
    print(f"\n[2/4] Classifying & filtering for relevant corporate events...")
    new_events = classify_and_filter(articles)
    print(f"  → {len(new_events)} new relevant events found")

    if not new_events:
        print("\n  No new events detected (all previously seen or below threshold).")
        print(f"  Summary: {len(articles)} scraped, 0 new events")
        return

    # Step 3: Format alerts
    print(f"\n[3/4] Formatting alerts...")
    alerts = []
    for event in new_events:
        cls = event.get("classification", {})
        alert_text = format_alert(event)
        alerts.append(alert_text)
        print(f"  📌 [{cls.get('event', '?')}] {event['title'][:80]}...")

    # Step 4: Send to Telegram
    print(f"\n[4/4] Sending {len(alerts)} alerts to Telegram...")
    if chat_id:
        await send_telegram_alerts(bot_token, chat_id, alerts)
        print(f"  → Alerts sent to chat_id: {chat_id}")
    else:
        print(f"  ⚠ No ALERT_CHAT_ID configured. Alerts generated but NOT sent.")
        print(f"  Set ALERT_CHAT_ID in .env to enable auto-sending.")
        # Print alerts to stdout as fallback
        print(f"\n{'=' * 60}")
        print(f"Generated Alerts (not sent):")
        print(f"{'=' * 60}")
        for i, alert in enumerate(alerts, 1):
            print(f"\n--- Alert {i}/{len(alerts)} ---")
            print(alert)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"PIPELINE SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Articles scraped:    {len(articles)}")
    print(f"  New events found:    {len(new_events)}")
    if new_events:
        event_types = {}
        for e in new_events:
            evt = e["classification"]["event"]
            event_types[evt] = event_types.get(evt, 0) + 1
        print(f"  Event breakdown:")
        for evt, cnt in sorted(event_types.items(), key=lambda x: -x[1]):
            print(f"    - {evt}: {cnt}")
    if chat_id:
        print(f"  Alerts sent:         {len(alerts)}")
    else:
        print(f"  Alerts sent:         0 (no chat_id configured)")


if __name__ == "__main__":
    asyncio.run(main())
