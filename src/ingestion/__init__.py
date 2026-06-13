"""
News Ingestion Pipeline — scrape Indonesian financial news, classify corporate events,
and alert Premium users in real-time.

Sources: Kontan, Bisnis.com, CNBC Indonesia
Classifier: TF-IDF + LogisticRegression (95.2% accuracy, 11 event classes)
"""
import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import urllib.request

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

PROJECT_ROOT = Path(__file__).parent.parent.parent
NEWS_STORE = PROJECT_ROOT / "data" / "news_seen.json"

SOURCES = {
    "kontan": {
        "name": "Kontan",
        "base": "https://kontan.co.id",
        "feed": "https://api.kontan.co.id/v2/news/headlines?limit=20",
        "type": "api",
    },
    "bisnis": {
        "name": "Bisnis.com",
        "base": "https://market.bisnis.com",
        "feed": "https://market.bisnis.com/indeks",
        "type": "html",
    },
    "cnbc": {
        "name": "CNBC Indonesia",
        "base": "https://www.cnbcindonesia.com",
        "feed": "https://www.cnbcindonesia.com/market/",
        "type": "html",
    },
}

EVENT_RELEVANT_LABELS = {
    "Dividend Announcements",
    "Share Buybacks",
    "Expansion (New Factory, Stores, Distribution Center, etc)",
    "Mergers and Acquisitions",
    "Initial Public Offerings (IPOs)",
    "Delistings",
    "Tender Offers",
    "Rights Issues",
}


def _load_seen() -> set:
    if NEWS_STORE.exists():
        with open(NEWS_STORE) as f:
            return set(json.load(f))
    return set()


def _save_seen(seen: set):
    NEWS_STORE.parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_STORE, "w") as f:
        json.dump(sorted(seen), f)


def _hash_url(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def scrape_kontan() -> list[dict]:
    """Scrape Kontan headlines via API."""
    try:
        req = urllib.request.Request(
            SOURCES["kontan"]["feed"],
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        articles = []
        for item in data.get("data", [])[:15]:
            title = item.get("title", "")
            url = item.get("url", "") or item.get("link", "")
            if title and "saham" in title.lower() or "bursa" in title.lower() or "ihsg" in title.lower():
                articles.append({
                    "title": title,
                    "url": url,
                    "source": "kontan",
                    "fetched_at": datetime.now(WIB).isoformat(),
                })
        return articles
    except Exception as e:
        logger.debug(f"Kontan scrape: {e}")
        return []


def scrape_bisnis() -> list[dict]:
    """Scrape Bisnis.com market news."""
    try:
        req = urllib.request.Request(
            SOURCES["bisnis"]["feed"],
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode()
        articles = []

        # Extract titles and links from HTML
        links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*saham[^<]*)</a>', html, re.I)
        for url, title in links:
            title = re.sub(r'<[^>]+>', '', title).strip()
            if title and len(title) > 20:
                full_url = url if url.startswith("http") else urljoin(SOURCES["bisnis"]["base"], url)
                articles.append({
                    "title": title,
                    "url": full_url,
                    "source": "bisnis",
                    "fetched_at": datetime.now(WIB).isoformat(),
                })
        return articles[:15]
    except Exception as e:
        logger.debug(f"Bisnis scrape: {e}")
        return []


def scrape_cnbc() -> list[dict]:
    """Scrape CNBC Indonesia market news."""
    try:
        req = urllib.request.Request(
            SOURCES["cnbc"]["feed"],
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode()
        articles = []

        titles = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
        links = re.findall(r'href="([^"]*)"', html)

        for title in titles[:20]:
            clean = re.sub(r'<[^>]+>', '', title).strip()
            if clean and len(clean) > 25:
                articles.append({
                    "title": clean,
                    "url": "",
                    "source": "cnbc",
                    "fetched_at": datetime.now(WIB).isoformat(),
                })
        return articles[:15]
    except Exception as e:
        logger.debug(f"CNBC scrape: {e}")
        return []


def scrape_all() -> list[dict]:
    """Scrape all sources. Deduplicate by title hash."""
    all_articles = []
    all_articles.extend(scrape_kontan())
    all_articles.extend(scrape_bisnis())
    all_articles.extend(scrape_cnbc())

    seen_titles = set()
    deduped = []
    for a in all_articles:
        key = a["title"].lower()[:60]
        if key not in seen_titles:
            seen_titles.add(key)
            deduped.append(a)

    return deduped


def classify_and_filter(articles: list[dict]) -> list[dict]:
    """Classify each article using event classifier. Keep only relevant events."""
    from src.engine.event_classifier import classify_news

    seen_urls = _load_seen()
    new_events = []

    for article in articles:
        url_hash = _hash_url(article["title"])
        if url_hash in seen_urls:
            continue

        try:
            result = classify_news(article["title"])
            if result["confidence"] < 25:
                continue
            if result["event"] not in EVENT_RELEVANT_LABELS:
                continue

            article["classification"] = result
            article["_hash"] = url_hash
            new_events.append(article)
            seen_urls.add(url_hash)
        except Exception as e:
            logger.debug(f"Classify failed: {e}")

    if new_events:
        _save_seen(seen_urls)

    return new_events


def format_alert(article: dict) -> str:
    """Format classified article into Telegram alert."""
    cls = article["classification"]
    emoji = {1: "🟢", 0: "🟡", -1: "🔴"}.get(cls["signal"], "⚪")

    lines = [
        f"{emoji} *{cls['event']}*",
        f"📰 {article['title'][:120]}",
        f"├ Source: {SOURCES.get(article['source'], {}).get('name', article['source'])}",
        f"├ Confidence: {cls['confidence']:.0f}% | Signal: {cls['impact']}",
    ]

    if article.get("url"):
        lines.append(f"└ [Baca selengkapnya]({article['url']})")

    return "\n".join(lines)


async def run_ingestion() -> list[dict]:
    """Full pipeline: scrape → classify → filter. Async wrapper."""
    loop = asyncio.get_running_loop()
    articles = await loop.run_in_executor(None, scrape_all)
    return classify_and_filter(articles)
