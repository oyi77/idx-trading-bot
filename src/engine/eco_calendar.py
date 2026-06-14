"""Economic Calendar — Indonesia-focused events that move IDX.

Hand-curated + auto-updated. Key events:
  • BI Rate Decision (monthly, ~3rd week)
  • Inflation CPI (monthly, 1st)
  • Trade Balance (monthly, ~15th)
  • GDP Growth (quarterly)
  • US FOMC (every ~6 weeks)
  • Rupiah denominated bond auctions

Commands:
  /calendar — this month's events
  /calendar next — next month
  /calendar all — known events ahead

Data source: manual curation + web scraping fallback.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class EcoEvent:
    date: str  # YYYY-MM-DD
    time: str  # HH:MM WIB or "All Day"
    title: str
    country: str  # ID, US, CN
    importance: str  # high, medium, low
    forecast: str = ""
    previous: str = ""
    impact: str = ""  # brief impact description


# ─── 2026 Key Events ─────────────────────────────────────────

ECO_EVENTS_2026 = [
    # BI Rate Decisions (monthly, ~3rd Wed)
    EcoEvent("2026-07-15", "14:00", "BI 7-Day Reverse Repo Rate", "ID", "high",
             forecast="5.75%", previous="5.75%",
             impact="Suku bunga acuan — gerakin IHSG & perbankan"),
    EcoEvent("2026-08-19", "14:00", "BI 7-Day Reverse Repo Rate", "ID", "high",
             forecast="", previous="",
             impact="Suku bunga acuan — gerakin IHSG & perbankan"),
    EcoEvent("2026-09-16", "14:00", "BI 7-Day Reverse Repo Rate", "ID", "high",
             forecast="", previous="",
             impact="Suku bunga acuan — gerakin IHSG & perbankan"),

    # Indonesia CPI (monthly, 1st)
    EcoEvent("2026-07-01", "11:00", "CPI Inflation YoY", "ID", "high",
             forecast="", previous="",
             impact="Inflasi menentukan arah suku bunga"),
    EcoEvent("2026-08-03", "11:00", "CPI Inflation YoY", "ID", "high",
             forecast="", previous="",
             impact="Inflasi menentukan arah suku bunga"),

    # Trade Balance (monthly, ~15th)
    EcoEvent("2026-07-15", "11:00", "Trade Balance", "ID", "medium",
             forecast="", previous="",
             impact="Surplus/deficit perdagangan — pengaruh ke Rupiah"),
    EcoEvent("2026-08-17", "11:00", "Trade Balance", "ID", "medium"),

    # GDP (quarterly)
    EcoEvent("2026-08-05", "11:00", "GDP Growth YoY Q2", "ID", "high",
             forecast="", previous="",
             impact="Pertumbuhan ekonomi — fundamental market"),

    # US FOMC (every ~6 weeks)
    EcoEvent("2026-07-29", "01:00", "FOMC Interest Rate Decision", "US", "high",
             forecast="", previous="",
             impact="Suku bunga AS — gerakin global market & Rupiah"),

    # US CPI
    EcoEvent("2026-07-14", "19:30", "US CPI YoY", "US", "high",
             forecast="", previous="",
             impact="Inflasi AS — ekspektasi Fed rate"),
    EcoEvent("2026-08-12", "19:30", "US CPI YoY", "US", "high"),

    # US NFP (monthly, 1st Friday)
    EcoEvent("2026-07-03", "19:30", "US Non-Farm Payrolls", "US", "high",
             impact="Data tenaga kerja AS — volatility USD/IDR"),
    EcoEvent("2026-08-07", "19:30", "US Non-Farm Payrolls", "US", "high"),

    # China data
    EcoEvent("2026-07-15", "09:00", "China GDP Q2", "CN", "high",
             impact="China = partner dagang terbesar — pengaruh komoditas"),
    EcoEvent("2026-07-10", "08:30", "China CPI YoY", "CN", "medium"),
]


def get_events_for_month(year: int, month: int) -> List[EcoEvent]:
    """Get all events for a given month."""
    prefix = f"{year}-{month:02d}"
    return [e for e in ECO_EVENTS_2026 if e.date.startswith(prefix)]


def get_upcoming_events(limit: int = 10) -> List[EcoEvent]:
    """Get next N upcoming events from today."""
    today = datetime.now().strftime("%Y-%m-%d")
    upcoming = [e for e in ECO_EVENTS_2026 if e.date >= today]
    upcoming.sort(key=lambda e: e.date)
    return upcoming[:limit]


def format_calendar(events: List[EcoEvent], title: str = "Economic Calendar") -> str:
    """Format events for Telegram."""
    if not events:
        return "📅 Tidak ada event ekonomi untuk periode ini."

    # Group by date
    grouped = {}
    for e in events:
        if e.date not in grouped:
            grouped[e.date] = []
        grouped[e.date].append(e)

    out = f"📅 *{title}*\n"
    out += "━━━━━━━━━━━━━━━━━━━━\n\n"

    for date_str, day_events in sorted(grouped.items()):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"][dt.weekday()]
        out += f"*{dt.day} {dt.strftime('%b')} ({day_name})*\n"

        for e in day_events:
            stars = {"high": "🔴🔴", "medium": "🟡", "low": "⚪"}.get(e.importance, "")
            flag = {"ID": "🇮🇩", "US": "🇺🇸", "CN": "🇨🇳"}.get(e.country, "")
            time_str = f" {e.time}" if e.time else ""
            out += f"  {stars} {flag} *{e.title}*{time_str}\n"
            if e.forecast:
                out += f"     Forecast: {e.forecast} | Prev: {e.previous}\n"
            if e.impact:
                out += f"     _{e.impact}_\n"

        out += "\n"

    out += "━━━━━━━━━━━━━━━━━━━━\n"
    out += "🔴🔴 High impact — potensi gerakin market signifikan"

    return out


def format_calendar_compact(events: List[EcoEvent]) -> str:
    """Compact format — just dates and titles."""
    if not events:
        return "📅 No upcoming events."

    out = "📅 *Upcoming Events*\n"
    out += "━━━━━━━━━━━━━━━━━━━━\n"

    for e in events[:8]:
        dt = datetime.strptime(e.date, "%Y-%m-%d")
        days_left = (dt - datetime.now()).days
        day_str = f"{days_left}d lagi" if days_left <= 7 else dt.strftime("%d %b")
        flag = {"ID": "🇮🇩", "US": "🇺🇸", "CN": "🇨🇳"}.get(e.country, "")
        stars = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(e.importance, "")
        out += f"  {stars} {flag} {day_str}: *{e.title}*\n"

    out += "━━━━━━━━━━━━━━━━━━━━\n"
    out += "💡 Detail: `/calendar`"

    return out
