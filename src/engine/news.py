"""News sentiment engine for IDX stocks.
Source: Google News RSS — free, no API key needed.

How it works:
1. Fetch RSS feed for \"<symbol> saham IDX\"
2. Filter by recency (default: last 7 days)
3. Score sentiment per article (keyword-based for Indonesian financial text)
4. Aggregate into overall sentiment score (0-10)
"""
import time
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class NewsItem:
    title: str
    source: str
    url: str
    published: datetime
    snippet: str = ""
    sentiment: str = "neutral"  # positive / negative / neutral
    confidence: float = 0.0


@dataclass
class SentimentReport:
    symbol: str
    score: float  # 0-10 (0=very bearish, 10=very bullish)
    articles: List[NewsItem] = field(default_factory=list)
    total_articles: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    summary: str = ""


class NewsEngine:
    """Fetch and analyze news sentiment for IDX stocks."""

    # Indonesian financial sentiment keywords
    _POSITIVE_WORDS = {
        # English
        "naik", "menguat", "bangkit", "rebound", "pemulihan", "buyback",
        "dividen", "bonus", "laba", "profit", "tumbuh", "growth",
        "positif", "optimis", "cerah", "kuat", "solid", "baik",
        "akuisisi", "ekspansi", "investasi", "rekomendasi", "beli",
        "terbang", "melonjak", "rally", "bullish", "outperform",
        "kepercayaan", "percaya diri", "performa", "kinerja baik",
        "tertahan", "stabil", "kenaikan", "peningkatan", "perbaikan",
        "untung", "cuan", "boncos",  # slang positive
        "overweight", "add", "accumulate",
    }
    
    _NEGATIVE_WORDS = {
        # Indonesian
        "turun", "melemah", "anjlok", "tertekan", "jatuh", "koreksi",
        "rugi", "merugi", "minus", "defisit", "hutang", "utang",
        "negatif", "pesimis", "suram", "lemah", "buruk", "krisis",
        "jual", "lepas", "dilepas", "divestasi", "tekanan",
        "ambruk", "runtuh", "hancur", "terjun", "freefall",
        "bearish", "underperform", "peringatan", "waspada",
        "turun drastis", "terpangkas", "terpotong", "terdepresiasi",
        "ketidakpastian", "risiko", "ancaman", "kekhawatiran",
        "terbebani", "tertahan", "penurunan", "pelemahan",
        "bencana", "gagal", "default", "pailit", "bangkrut",
        "PHK", "pemutusan", "skandal", "korupsi",
        "underweight", "reduce", "sell", "cut",
    }

    def __init__(self, max_days: int = 7, max_articles: int = 5):
        self.max_days = max_days
        self.max_articles = max_articles

    async def analyze(self, symbol: str) -> SentimentReport:
        """Fetch news and analyze sentiment for a stock."""
        articles = await self._fetch_news(symbol)
        report = self._compute_sentiment(symbol, articles)
        return report

    async def _fetch_news(self, symbol: str) -> List[NewsItem]:
        """Fetch Google News RSS for the given symbol."""
        import aiohttp
        import xml.etree.ElementTree as ET

        query = f"{symbol} saham IDX"
        url = (
            "https://news.google.com/rss/search?"
            f"q={_url_encode(query)}&hl=id&gl=ID&ceid=ID:id"
        )

        articles = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.max_days)

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                }
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        return []
                    text = await resp.text()

            root = ET.fromstring(text)
            ns = {"": "http://www.w3.org/2005/Atom"}  # Google uses Atom

            for item in root.findall(".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate")
                source_el = item.find("source")
                desc_el = item.find("description")

                title = title_el.text.strip() if title_el is not None else ""
                raw_link = link_el.text.strip() if link_el is not None else ""
                pub_str = pub_el.text.strip() if pub_el is not None else ""
                source = source_el.text.strip() if source_el is not None else "Unknown"

                # Parse description for snippet
                snippet = ""
                if desc_el is not None and desc_el.text:
                    match = re.search(r'<font[^>]*>(.*?)</font>', desc_el.text, re.DOTALL)
                    if match:
                        snippet = match.group(1).strip()

                # Parse date
                published = self._parse_date(pub_str)
                if not published:
                    continue

                # Filter by recency
                if published < cutoff:
                    continue

                articles.append(NewsItem(
                    title=title,
                    source=source,
                    url=raw_link,
                    published=published,
                    snippet=snippet,
                ))

                if len(articles) >= self.max_articles:
                    break

            return articles

        except Exception as e:
            print(f"[NewsEngine] Error fetching for {symbol}: {e}")
            return []

    def _compute_sentiment(self, symbol: str, articles: List[NewsItem]) -> SentimentReport:
        """Keyword-based sentiment scoring for Indonesian financial news."""
        if not articles:
            return SentimentReport(
                symbol=symbol, score=5.0,
                summary="Tidak ada berita terkini untuk saham ini dalam 7 hari terakhir."
            )

        total_score = 0.0
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for article in articles:
            text = f"{article.title} {article.snippet}".lower()
            pos_score = sum(1 for w in self._POSITIVE_WORDS if w in text)
            neg_score = sum(1 for w in self._NEGATIVE_WORDS if w in text)

            if pos_score > neg_score:
                article.sentiment = "positive"
                article.confidence = min((pos_score - neg_score) / max(pos_score + neg_score, 1), 1.0)
                positive_count += 1
                total_score += 1.0
            elif neg_score > pos_score:
                article.sentiment = "negative"
                article.confidence = min((neg_score - pos_score) / max(pos_score + neg_score, 1), 1.0)
                negative_count += 1
                total_score += 0.0
            else:
                article.sentiment = "neutral"
                article.confidence = 0.5
                neutral_count += 1
                total_score += 0.5

        n = len(articles)
        avg_score = (total_score / n) if n > 0 else 0.5
        normalized = round(avg_score * 10, 1)

        # Generate summary
        if positive_count > negative_count and positive_count > neutral_count:
            summary = f"Sentimen cenderung POSITIF ({normalized}/10)"
        elif negative_count > positive_count:
            summary = f"Sentimen cenderung NEGATIF ({normalized}/10)"
        else:
            summary = f"Sentimen NETRAL ({normalized}/10)"

        # Add highlights
        for article in articles[:3]:
            emoji = "🟢" if article.sentiment == "positive" else ("🔴" if article.sentiment == "negative" else "⚪")
            short_title = article.title[:80] + "..." if len(article.title) > 80 else article.title
            days_ago = (datetime.now(timezone.utc) - article.published).days
            time_str = f"{days_ago}h" if days_ago == 0 else f"{days_ago}h" if days_ago < 24 else f"{days_ago}h"

            # Don't add to summary here, just mark

        return SentimentReport(
            symbol=symbol,
            score=normalized,
            articles=articles[:self.max_articles],
            total_articles=len(articles),
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            summary=summary,
        )

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS pubDate format."""
        formats = [
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return None


def _url_encode(text: str) -> str:
    """Simple URL encoding."""
    import urllib.parse
    return urllib.parse.quote(text)
