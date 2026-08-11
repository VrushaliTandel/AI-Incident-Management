"""
Analytics service: computes metrics and time-series data for the admin dashboard.
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.database.models import Incident, User
from backend.database.repository import get_dashboard_stats

logger = logging.getLogger(__name__)


def get_admin_analytics(db: Session) -> Dict[str, Any]:
    """Return comprehensive analytics data."""
    stats = get_dashboard_stats(db)

    # Incidents over last 30 days (daily)
    now = datetime.now(timezone.utc)
    time_series = []
    for i in range(29, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = (
            db.query(func.count(Incident.id))
            .filter(Incident.created_at >= day_start, Incident.created_at < day_end)
            .scalar() or 0
        )
        time_series.append({"date": day_start.strftime("%Y-%m-%d"), "count": count})

    # Incidents by resolution level
    by_level = {}
    for level in ["L1", "L2", "L3", "HUMAN_HANDOFF", ""]:
        cnt = (
            db.query(func.count(Incident.id))
            .filter(Incident.resolution_level == level)
            .scalar() or 0
        )
        label = level if level else "In Progress"
        by_level[label] = cnt

    # Incidents by status
    by_status = {
        "RESOLVED": stats["resolved"],
        "ESCALATED": stats["escalated"],
        "IN_PROGRESS": stats["in_progress"],
    }

    # Incidents per user (top 10)
    user_counts = (
        db.query(User.username, func.count(Incident.id).label("cnt"))
        .join(Incident, Incident.user_id == User.id)
        .group_by(User.id)
        .order_by(desc("cnt"))
        .limit(10)
        .all()
    )
    by_user = [{"username": r[0], "count": r[1]} for r in user_counts]

    # Average resolution time (for resolved incidents)
    resolved_incidents = (
        db.query(Incident.created_at, Incident.updated_at)
        .filter(Incident.status == "RESOLVED")
        .all()
    )
    avg_resolution_minutes = None
    if resolved_incidents:
        durations = []
        for created, updated in resolved_incidents:
            if created and updated:
                # Handle both naive and aware datetimes
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                delta = (updated - created).total_seconds() / 60
                if delta >= 0:
                    durations.append(delta)
        if durations:
            avg_resolution_minutes = round(sum(durations) / len(durations), 1)

    # ── Voice / language distribution ─────────────────────────────
    # Detect script/language from stored user_query text using Unicode blocks.
    # No DB schema change needed — derived at query time.
    queries = db.query(Incident.user_query).all()
    lang_counts: Dict[str, int] = {}
    for (q,) in queries:
        lang = _detect_script_language(q or "")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # Incidents with non-Latin script queries (typed/spoken in a non-English language)
    non_english = sum(v for k, v in lang_counts.items() if k != "English")
    multilingual_rate = round(non_english / len(queries) * 100, 1) if queries else 0.0

    # Resolution time by tier
    tier_avg: Dict[str, Any] = {}
    for tier in ("L1", "L2", "L3", "HUMAN_HANDOFF"):
        tier_rows = (
            db.query(Incident.created_at, Incident.updated_at)
            .filter(Incident.resolution_level == tier, Incident.status == "RESOLVED")
            .all()
        )
        if tier_rows:
            durs = []
            for c, u in tier_rows:
                if c and u:
                    if c.tzinfo is None:
                        c = c.replace(tzinfo=timezone.utc)
                    if u.tzinfo is None:
                        u = u.replace(tzinfo=timezone.utc)
                    d = (u - c).total_seconds() / 60
                    if d >= 0:
                        durs.append(d)
            tier_avg[tier] = round(sum(durs) / len(durs), 1) if durs else None
        else:
            tier_avg[tier] = None

    return {
        **stats,
        "time_series": time_series,
        "by_resolution_level": by_level,
        "by_status": by_status,
        "by_user": by_user,
        "avg_resolution_minutes": avg_resolution_minutes,
        # Voice / language analytics
        "language_distribution": lang_counts,
        "multilingual_rate": multilingual_rate,
        "non_english_incidents": non_english,
        # Per-tier resolution times
        "avg_resolution_by_tier": tier_avg,
    }


def _detect_script_language(text: str) -> str:
    """Classify a query string into a broad language label using Unicode block heuristics."""
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi/Devanagari"
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "Tamil"
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "Telugu"
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "Kannada"
    if re.search(r"[\u0D00-\u0D7F]", text):
        return "Malayalam"
    if re.search(r"[\u0980-\u09FF]", text):
        return "Bengali"
    if re.search(r"[\u0A80-\u0AFF]", text):
        return "Gujarati"
    if re.search(r"[\u0600-\u06FF]", text):
        return "Arabic/Urdu"
    if re.search(r"[\u4E00-\u9FFF]", text):
        return "Chinese"
    if re.search(r"[\u3040-\u30FF]", text):
        return "Japanese"
    if re.search(r"[\uAC00-\uD7AF]", text):
        return "Korean"
    if re.search(r"[\u0400-\u04FF]", text):
        return "Cyrillic"
    return "English"
