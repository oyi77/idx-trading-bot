"""Gamification Engine — points, leaderboard, achievements.

Simple JSON-based persistence. No DB dependency.

Actions & Points:
  analisa        +1  (max 5/day)
  feedback       +2  (unlimited)
  plan_trade     +3  (max 10/day)
  watchlist_add  +1  (max 5/day)
  daily_login    +1  (once/day)

Leaderboard: weekly, monthly, all-time.
"""

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


POINTS_DIR = os.path.expanduser("~/idx-trading-bot/data/gamification")


ACTION_POINTS = {
    "analisa": 1,
    "feedback": 2,
    "plan_trade": 3,
    "watchlist_add": 1,
    "daily_login": 1,
}

DAILY_LIMITS = {
    "analisa": 5,
    "plan_trade": 10,
    "watchlist_add": 5,
    "daily_login": 1,
}


@dataclass
class UserPoints:
    user_id: int
    username: str = ""
    total_points: int = 0
    weekly_points: int = 0
    monthly_points: int = 0
    rank: int = 0
    streak: int = 0  # consecutive days active


class GamificationEngine:
    """Track user points and generate leaderboards."""

    def __init__(self):
        os.makedirs(POINTS_DIR, exist_ok=True)

    def _path(self, user_id: int) -> str:
        return os.path.join(POINTS_DIR, f"points_{user_id}.json")

    def _load(self, user_id: int) -> dict:
        path = self._path(user_id)
        if not os.path.exists(path):
            return {"user_id": user_id, "log": [], "streak": 0, "last_login": None}
        with open(path) as f:
            return json.load(f)

    def _save(self, user_id: int, data: dict):
        with open(self._path(user_id), "w") as f:
            json.dump(data, f, indent=2)

    def award(self, user_id: int, action: str, username: str = "") -> Tuple[bool, str]:
        """Award points for an action. Returns (success, message)."""
        if action not in ACTION_POINTS:
            return False, f"Unknown action: {action}"

        data = self._load(user_id)
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # Check daily limits
        if action in DAILY_LIMITS:
            today_count = sum(
                1 for entry in data.get("log", [])
                if entry.get("action") == action
                and entry.get("timestamp", "").startswith(today_str)
            )
            if today_count >= DAILY_LIMITS[action]:
                return False, f"Daily limit reached for {action} ({DAILY_LIMITS[action]}x/day)"

        # Check daily login once
        if action == "daily_login" and data.get("last_login") == today_str:
            return False, "Already logged in today"

        # Award points
        points = ACTION_POINTS[action]
        data.setdefault("log", []).append({
            "action": action,
            "points": points,
            "timestamp": now.isoformat(),
        })

        # Update streak
        if action == "daily_login":
            data["last_login"] = today_str
            last = data.get("last_login")
            if last:
                try:
                    last_date = datetime.fromisoformat(last).date()
                    if (now.date() - last_date).days == 1:
                        data["streak"] = data.get("streak", 0) + 1
                    elif (now.date() - last_date).days > 1:
                        data["streak"] = 1
                except (ValueError, TypeError):
                    data["streak"] = 1
            else:
                data["streak"] = 1

        if username:
            data["username"] = username

        self._save(user_id, data)
        return True, f"+{points} point{'s' if points > 1 else ''} ({action})"

    def get_points(self, user_id: int) -> dict:
        """Get user's points + rank for all periods."""
        data = self._load(user_id)
        now = datetime.now()
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        month_start = now.strftime("%Y-%m-01")

        total = sum(e["points"] for e in data.get("log", []))
        weekly = sum(
            e["points"] for e in data.get("log", [])
            if e["timestamp"] >= week_start
        )
        monthly = sum(
            e["points"] for e in data.get("log", [])
            if e["timestamp"] >= month_start
        )

        # Calculate rank (weekly)
        all_users = self._load_all()
        weekly_scores = []
        for uid, udata in all_users.items():
            ws = sum(
                e["points"] for e in udata.get("log", [])
                if e["timestamp"] >= week_start
            )
            weekly_scores.append((uid, ws))
        weekly_scores.sort(key=lambda x: x[1], reverse=True)
        rank = next((i + 1 for i, (uid, _) in enumerate(weekly_scores) if uid == user_id), 0)

        return {
            "user_id": user_id,
            "username": data.get("username", ""),
            "total_points": total,
            "weekly_points": weekly,
            "monthly_points": monthly,
            "rank": rank,
            "streak": data.get("streak", 0),
            "total_users": len(all_users),
        }

    def get_leaderboard(self, period: str = "weekly", limit: int = 10) -> List[dict]:
        """Get top users for a period. period: weekly, monthly, all_time."""
        all_users = self._load_all()
        now = datetime.now()

        if period == "weekly":
            cutoff = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        elif period == "monthly":
            cutoff = now.strftime("%Y-%m-01")
        else:  # all_time
            cutoff = "1970-01-01"

        scored = []
        for uid, data in all_users.items():
            pts = sum(
                e["points"] for e in data.get("log", [])
                if e["timestamp"] >= cutoff
            )
            if pts > 0:
                scored.append({
                    "user_id": uid,
                    "username": data.get("username", f"User{uid}"),
                    "points": pts,
                    "streak": data.get("streak", 0),
                })

        scored.sort(key=lambda x: x["points"], reverse=True)
        return scored[:limit]

    def _load_all(self) -> Dict[int, dict]:
        """Load all user point files."""
        users = {}
        for fname in os.listdir(POINTS_DIR):
            if fname.startswith("points_") and fname.endswith(".json"):
                try:
                    uid = int(fname.replace("points_", "").replace(".json", ""))
                    users[uid] = self._load(uid)
                except (ValueError, Exception):
                    pass
        return users

    def format_leaderboard(self, entries: List[dict], period: str = "weekly") -> str:
        """Format leaderboard for Telegram output."""
        period_labels = {
            "weekly": "Minggu Ini",
            "monthly": "Bulan Ini",
            "all_time": "Sepanjang Masa",
        }
        label = period_labels.get(period, period)

        out = f"🏆 *Leaderboard — {label}*\n"
        out += "━━━━━━━━━━━━━━━━━━━━\n\n"

        if not entries:
            out += "Belum ada pemain. Mulai trading untuk kumpulin poin!\n\n"
            out += "💡 `/analisa BBCA` → +1 poin\n"
            return out

        medals = ["🥇", "🥈", "🥉"] + [f"  {i}." for i in range(4, len(entries) + 1)]
        for i, entry in enumerate(entries):
            medal = medals[i] if i < len(medals) else f"  {i+1}."
            streak = f" 🔥{entry['streak']}d" if entry.get("streak") else ""
            out += f"{medal} *{entry['username']}* — {entry['points']} pts{streak}\n"

        out += "\n━━━━━━━━━━━━━━━━━━━━\n"
        out += "💡 `/points` untuk liat skor kamu\n"
        out += "📊 Dapetin poin: analisa (+1), feedback (+2), plan (+3)"

        return out

    def format_points(self, data: dict) -> str:
        """Format user's personal points card."""
        total = data["total_points"]
        rank = data["rank"]
        streak = data["streak"]

        level = "🟢 Trader" if total < 50 else ("🔵 Pro" if total < 200 else ("🟣 Master" if total < 500 else "👑 Legend"))

        out = f"⭐ *Poin Kamu*\n"
        out += "━━━━━━━━━━━━━━━━━━━━\n\n"
        out += f"🏅 Level: *{level}*\n"
        out += f"📊 Total: *{total} pts*\n"
        out += f"📅 Minggu ini: *{data['weekly_points']} pts*\n"
        out += f"📆 Bulan ini: *{data['monthly_points']} pts*\n"
        out += f"🔥 Streak: *{streak} hari*\n"
        out += f"🏆 Rank minggu ini: *#{rank}* dari {data['total_users']} trader\n\n"
        out += "━━━━━━━━━━━━━━━━━━━━\n"
        out += "📊 *Cara dapetin poin:*\n"
        out += "• /analisa → +1 (max 5/hari)\n"
        out += "• /feedback → +2\n"
        out += "• /plan → +3 (max 10/hari)\n"
        out += "• /watchlist add → +1 (max 5/hari)\n\n"
        out += "🏆 `/leaderboard` untuk liat top trader"

        return out


# ── Singleton ──────────────────────────────────────────────────

_engine: Optional[GamificationEngine] = None


def get_engine() -> GamificationEngine:
    global _engine
    if _engine is None:
        _engine = GamificationEngine()
    return _engine


# ── Convenience helpers ────────────────────────────────────────

def award(user_id: int, action: str, username: str = "") -> Tuple[bool, str]:
    return get_engine().award(user_id, action, username)


def get_leaderboard(period: str = "weekly", limit: int = 10) -> List[dict]:
    return get_engine().get_leaderboard(period, limit)
