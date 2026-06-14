"""Trading Journal — Record trade lessons & insights.

Commands:
  /journal                      — last 5 entries
  /journal add <text>           — add entry
  /journal list [page]          — paginated list
  /journal delete <id>          — delete entry

Storage: JSON per user in data/journal/
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple


JOURNAL_DIR = os.path.expanduser("~/idx-trading-bot/data/journal")


@dataclass
class JournalEntry:
    entry_id: int
    user_id: int
    text: str
    symbol: str = ""
    timestamp: str = ""
    tags: list = field(default_factory=list)


class JournalEngine:
    """Simple trading journal with JSON persistence."""

    def __init__(self):
        os.makedirs(JOURNAL_DIR, exist_ok=True)

    def _path(self, user_id: int) -> str:
        return os.path.join(JOURNAL_DIR, f"journal_{user_id}.json")

    def load(self, user_id: int) -> List[JournalEntry]:
        path = self._path(user_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                data = json.load(f)
            return [
                JournalEntry(
                    entry_id=d.get("entry_id", 0),
                    user_id=d.get("user_id", user_id),
                    text=d.get("text", ""),
                    symbol=d.get("symbol", ""),
                    timestamp=d.get("timestamp", ""),
                    tags=d.get("tags", []),
                )
                for d in data
            ]
        except Exception:
            return []

    def save(self, user_id: int, entries: List[JournalEntry]):
        data = [
            {
                "entry_id": e.entry_id,
                "user_id": e.user_id,
                "text": e.text,
                "symbol": e.symbol,
                "timestamp": e.timestamp,
                "tags": e.tags,
            }
            for e in entries
        ]
        with open(self._path(user_id), "w") as f:
            json.dump(data, f, indent=2)

    def add(self, user_id: int, text: str, symbol: str = "") -> Tuple[bool, str]:
        """Add a journal entry. Auto-extracts #tags and $symbol."""
        entries = self.load(user_id)

        # Auto-extract tags
        tags = [w[1:] for w in text.split() if w.startswith("#")]

        # Auto-extract symbol if not provided
        if not symbol:
            for word in text.split():
                clean = word.strip(",.!?").upper()
                if len(clean) == 4 and clean.isalpha() and clean not in (
                    "BUY", "SELL", "HOLD", "KEYS", "LESS", "NOTE", "IDEA",
                    "LOSS", "PROF", "RISK", "PLAN", "STOP", "EXIT", "ENTR",
                    "PULL", "WAIT", "OVER", "SIZE", "FROM", "WITH", "THAT",
                    "THIS", "WHEN", "WHAT", "THEN", "MORE", "LESS", "GOOD",
                    "BEST", "NEXT", "LAST", "SAME", "LIKE", "JUST", "WEEK",
                    "SESI", "PASAR", "LAPOR", "SELES", "CASH",
                ):
                    symbol = clean
                    break

        entry_id = max((e.entry_id for e in entries), default=0) + 1
        entry = JournalEntry(
            entry_id=entry_id,
            user_id=user_id,
            text=text,
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
            tags=tags,
        )
        entries.append(entry)
        self.save(user_id, entries)

        symbol_str = f" [{symbol}]" if symbol else ""
        return True, f"📓 Journal #{entry_id}{symbol_str} tersimpan.\n\n{text[:200]}"

    def delete(self, user_id: int, entry_id: int) -> Tuple[bool, str]:
        """Delete a journal entry by ID."""
        entries = self.load(user_id)
        new_entries = [e for e in entries if e.entry_id != entry_id]
        if len(new_entries) == len(entries):
            return False, f"Entry #{entry_id} tidak ditemukan."
        self.save(user_id, new_entries)
        return True, f"✅ Entry #{entry_id} dihapus."

    def format_entries(self, entries: List[JournalEntry], page: int = 1, per_page: int = 5) -> str:
        """Format journal entries for Telegram."""
        if not entries:
            return (
                "📓 *Trading Journal*\n\n"
                "Belum ada catatan. Mulai dengan:\n"
                "`/journal add TLKM entry 4500 exit 4800 — sabar nunggu pullback ke support`\n\n"
                "💡 Auto-ekstrak #tags dan \$symbol"
            )

        total = len(entries)
        start = (page - 1) * per_page
        page_entries = entries[start:start + per_page]
        total_pages = (total + per_page - 1) // per_page

        out = f"📓 *Trading Journal*"
        if total_pages > 1:
            out += f"  ({page}/{total_pages})"
        out += "\n━━━━━━━━━━━━━━━━━━━━\n\n"

        for e in page_entries:
            ts = e.timestamp[:16].replace("T", " ") if e.timestamp else "?"
            symbol_str = f" *{e.symbol}*" if e.symbol else ""
            out += f"*#{e.entry_id}*{symbol_str} — {ts}\n"
            out += f"{e.text[:300]}\n"
            if e.tags:
                out += f"`{' '.join('#' + t for t in e.tags)}`\n"
            out += "\n"

        if total_pages > 1:
            out += f"Page {page}/{total_pages} — `/journal list {page+1}` untuk lanjut\n"

        out += "━━━━━━━━━━━━━━━━━━━━\n"
        out += "💡 Tambah: `/journal add <catatan>`  |  Hapus: `/journal delete <id>`"

        return out

    def get_stats(self, entries: List[JournalEntry]) -> dict:
        """Get journal stats."""
        symbols = {}
        tags = {}
        for e in entries:
            if e.symbol:
                symbols[e.symbol] = symbols.get(e.symbol, 0) + 1
            for t in e.tags:
                tags[t] = tags.get(t, 0) + 1

        return {
            "total": len(entries),
            "top_symbols": sorted(symbols.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_tags": sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5],
        }
