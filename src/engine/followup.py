"""
Autonomous Follow-Up Engine — the money machine.

Segments:
  new          = just joined, < 3 commands, < 24h old
  active_free  = uses bot regularly but never paid
  sleeping     = hasn't used bot in 3+ days (free tier)
  power_free   = 50+ commands, still free → hot lead
  paid_churn   = subscription expired, inactive

Stages:
  0 = no follow-up sent yet
  1 = gentle nudge (value reminder)
  2 = urgency / FOMO (limited time, what they're missing)
  3 = last attempt / exit survey → then stop

Guard: minimum 48h between follow-ups. Max 3 per user.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import logging

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))


class Segment(str, Enum):
    NEW = "new"
    ACTIVE_FREE = "active_free"
    SLEEPING = "sleeping"
    POWER_FREE = "power_free"
    PAID_CHURN = "paid_churn"


# ── Segment classifier ──

def classify_user(user_row) -> Optional[Segment]:
    """Determine user segment from DB row."""
    now = datetime.now(WIB)
    age_hours = (now - user_row.created_at.replace(tzinfo=WIB)).total_seconds() / 3600 if user_row.created_at else 999

    sub = getattr(user_row, 'subscription', None)
    tier = sub.tier if sub else "free"

    if tier != "free":
        # Check if subscription expired
        if sub and sub.end_date:
            end = sub.end_date.replace(tzinfo=WIB) if sub.end_date.tzinfo is None else sub.end_date
            if end < now:
                return Segment.PAID_CHURN
        return None  # paid users don't get follow-up

    activity = getattr(user_row, 'activity_count', 0) or 0
    last_active = getattr(user_row, 'last_active', None)

    # Power user: 50+ commands, still free
    if activity >= 50:
        return Segment.POWER_FREE

    # Sleeping: no activity in 3+ days
    if last_active:
        la = last_active.replace(tzinfo=WIB) if last_active.tzinfo is None else last_active
        days_inactive = (now - la).days
        if days_inactive >= 3:
            return Segment.SLEEPING

    # New: < 24h old AND < 3 commands
    if age_hours < 24 and activity < 3:
        return Segment.NEW

    # Active free
    return Segment.ACTIVE_FREE


# ── Message templates ──

FOLLOWUP_MESSAGES = {
    Segment.NEW: {
        1: (
            "👋 *Selamat datang di Vilona Saham!*\n\n"
            "Lo udah coba `/analisa BBCA`? AI gw bisa baca teknikal + bandar flow + "
            "fundamental dalam 1 perintah natural.\n\n"
            "🔥 *Coba sekarang:* ketik `/analisa TLKM`\n"
            "📖 *Panduan lengkap:* /panduan"
        ),
        2: (
            "📊 *Tau gak?* Trader pro rata-rata hemat 2 jam/hari pake AI analysis.\n\n"
            "Daripada lo scroll chart manual, mending `/analisa <saham>` "
            "dan dapet full breakdown dalam 10 detik.\n\n"
            "🎯 *Coba:* `/analisa BBRI` — liat sinyal teknikal + rekomendasi SL/TP."
        ),
        3: (
            "🚀 *Last call!* Gw notice lo belum eksplor fitur premium nih.\n\n"
            "Coba `/screener momentum` — nemuin saham yang lagi trending "
            "sebelum orang lain tau.\n\n"
            "💎 Upgrade ke Pro cuma Rp49rb/bln: /upgrade"
        ),
    },
    Segment.ACTIVE_FREE: {
        1: (
            "💡 *Lo pake Vilona Saham terus — keren!*\n\n"
            "Tapi lo masih di tier Free nih. Tau gak yang lo lewatin?\n"
            "• Real-time data (bukan delay 15 menit)\n"
            "• 50 alert harga (bukan cuma 5)\n"
            "• Bandarmology — liat jejak bandar real-time\n\n"
            "💎 Upgrade Pro Rp49rb/bln: /upgrade"
        ),
        2: (
            "📈 *Trader serius gak pake Free tier.*\n\n"
            "Dengan Premium (Rp149rb/bln), lo dapet:\n"
            "• AI trade setup otomatis + narasi\n"
            "• Screener unlimited (momentum, breakout, smart money)\n"
            "• Grup eksklusif + sesi mentor mingguan\n\n"
            "🔥 /upgrade sekarang — cancel kapan aja."
        ),
        3: (
            "⚠️ *Lo udah 3x gw ingetin bro.*\n\n"
            "Ini tawaran terakhir: upgrade ke Pro dan gw kasih "
            "*bonus 3 hari trial Premium* gratis.\n\n"
            "Balas chat ini buat klaim, atau /upgrade langsung."
        ),
    },
    Segment.POWER_FREE: {
        1: (
            "🔥 *Power user detected!* Lo udah 50+ analisa — gila.\n\n"
            "Dengan volume segitu, lo BUTUH real-time data + alert unlimited.\n"
            "Free tier lo cuma 5 alert — itu kurang banget buat trader aktif.\n\n"
            "💎 /upgrade ke Pro sekarang — Rp49rb doang."
        ),
        2: (
            "⚡ *Lo tau gak?* Power user kaya lo biasanya upgrade dalam 7 hari.\n\n"
            "Jangan sampe ketinggalan momentum market karena data delay.\n"
            "Pro = real-time. Free = delay 15 menit.\n\n"
            "Di market saham, 15 menit = cuan atau boncos.\n"
            "💎 /upgrade"
        ),
    },
    Segment.SLEEPING: {
        1: (
            "😴 *Halo! Udah 3+ hari gak buka Vilona Saham.*\n\n"
            "Market gak tidur bro. Coba cek kondisi terbaru:\n"
            "• `/ihsg` — IHSG hari ini\n"
            "• `/topgainers` — saham paling cuan\n"
            "• `/analisa BBCA` — full AI breakdown\n\n"
            "Gas, 10 detik doang."
        ),
        2: (
            "📉 *Lo ketinggalan nih.* Market IDX minggu ini volatile — "
            "banyak peluang entry.\n\n"
            "Coba `/screener momentum` buat liat saham yang lagi trending.\n"
            "Atau `/analisa <saham>` buat liat setup teknikal.\n\n"
            "Gak ada biaya — masih gratis kok."
        ),
        3: (
            "👋 *Terakhir dari gw.* Kalo lo udah gak butuh, gak pa-pa.\n\n"
            "Tapi kalo lo masih trading, gw masih di sini.\n"
            "Bot tetap gratis, tinggal ketik aja.\n\n"
            "📖 /panduan — semua fitur gratis yang lo bisa pake."
        ),
    },
    Segment.PAID_CHURN: {
        1: (
            "⚠️ *Langganan lo udah expired.*\n\n"
            "Fitur premium udah gak aktif. Lo balik ke Free tier.\n\n"
            "🔥 Re-activate sekarang: /upgrade\n"
            "Gak perlu daftar ulang — tinggal bayar, langsung aktif lagi."
        ),
        2: (
            "💔 *Gw notice lo belum renew.*\n\n"
            "Banyak fitur yang lo lewatin: real-time data, screener unlimited, "
            "alert 50-200, bandarmology.\n\n"
            "🔥 /upgrade — harga tetap sama, gak naik."
        ),
    },
}


# ── Stage timing ──

STAGE_DELAY_HOURS = {
    1: 24,   # Stage 1: 24h after last follow-up or signup
    2: 72,   # Stage 2: 3 days after stage 1
    3: 120,  # Stage 3: 5 days after stage 2
}

MAX_FOLLOWUP_STAGE = 3
MIN_HOURS_BETWEEN_FOLLOWUPS = 48


def get_message(segment: Segment, stage: int) -> Optional[str]:
    """Get follow-up message for segment + stage."""
    seg_msgs = FOLLOWUP_MESSAGES.get(segment, {})
    return seg_msgs.get(stage)


def should_followup(user_row) -> tuple[bool, Optional[str], Optional[int]]:
    """Check if user should receive a follow-up message.
    
    Returns: (should_send, segment, next_stage)
    """
    now = datetime.now(WIB)

    # Don't follow-up paid active users
    sub = getattr(user_row, 'subscription', None)
    if sub and sub.tier != "free":
        end = sub.end_date
        if end:
            end = end.replace(tzinfo=WIB) if end.tzinfo is None else end
            if end > now:
                return False, None, None
        else:
            return False, None, None

    segment = classify_user(user_row)
    if segment is None:
        return False, None, None

    stage = getattr(user_row, 'followup_stage', 0) or 0
    
    # Max stage reached
    if stage >= MAX_FOLLOWUP_STAGE:
        return False, None, None

    # Anti-spam: check last follow-up time
    last_fu = getattr(user_row, 'last_followup_at', None)
    if last_fu:
        last_fu = last_fu.replace(tzinfo=WIB) if last_fu.tzinfo is None else last_fu
        hours_since = (now - last_fu).total_seconds() / 3600
        if hours_since < MIN_HOURS_BETWEEN_FOLLOWUPS:
            return False, None, None

    # Stage timing
    target_stage = stage + 1
    target_delay = STAGE_DELAY_HOURS.get(target_stage, 24)
    
    if stage == 0:
        # No follow-up yet — check if enough time since signup
        # Active users (3+ commands): minimum 10 minutes. New users: 2h.
        created = user_row.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=WIB)
        if created:
            hours_elapsed = (now - created).total_seconds() / 3600
            min_hours = 0.15 if (getattr(user_row, 'activity_count', 0) or 0) >= 3 else 2.0
            if hours_elapsed < min_hours:
                return False, None, None
    else:
        # Check if enough time since last stage
        if last_fu:
            hours_since_last = (now - last_fu).total_seconds() / 3600
            if hours_since_last < target_delay:
                return False, None, None

    return True, segment.value, target_stage
