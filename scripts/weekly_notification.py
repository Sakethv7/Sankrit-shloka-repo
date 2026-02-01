"""Vedic Wisdom Weekly — main notification generator.

Fetches real Telugu Panchangam data via Swiss Ephemeris, matches
observances for the week, pairs them with Sanskrit verses, and
outputs a weekly digest. Logs all runs to MLflow.
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from panchang import compute, is_ekadashi, is_pradosham, is_amavasya, is_purnima, is_chaturthi, DailyPanchang

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

_VERSE_SEARCH_DIR = Path(__file__).resolve().parent.parent / "skills" / "sanskrit-wisdom" / "scripts"
_TRACKER_DIR = Path(__file__).resolve().parent.parent / "skills" / "ml-experiment"
sys.path.insert(0, str(_VERSE_SEARCH_DIR))
sys.path.insert(0, str(_TRACKER_DIR))
from verse_search import semantic_search, search as keyword_search, Verse
from tracker import log_notification


# ── Data Models ──────────────────────────────────────────────────────

@dataclass
class Observance:
    name: str
    date: dt.date
    deity: str
    description: str = ""


@dataclass
class WeeklyDigest:
    week_start: dt.date
    week_end: dt.date
    panchang_days: list[DailyPanchang] = field(default_factory=list)
    observances: list[Observance] = field(default_factory=list)
    verse: dict | None = None


# ── Observance Detection ─────────────────────────────────────────────

OBSERVANCE_CHECKS = [
    (is_ekadashi, "Ekadashi", "Vishnu", "Fast and Vishnu worship"),
    (is_pradosham, "Pradosham", "Shiva", "Shiva puja during twilight"),
    (is_amavasya, "Amavasya", "Pitrus", "Tarpanam for ancestors"),
    (is_purnima, "Purnima", "All", "Full moon observance"),
    (is_chaturthi, "Sankashti Chaturthi", "Ganesha", "Ganesha vrata"),
]


def _detect_observances(p: DailyPanchang, day: dt.date) -> list[Observance]:
    """Check a single day's panchang against all observance rules."""
    return [Observance(name=n, date=day, deity=d, description=desc) for fn, n, d, desc in OBSERVANCE_CHECKS if fn(p)]


def get_week_data(start: dt.date) -> tuple[list[DailyPanchang], list[Observance]]:
    """Compute panchangam and detect observances for a 7-day window."""
    days = [compute(start + dt.timedelta(days=i)) for i in range(7)]
    dates = [start + dt.timedelta(days=i) for i in range(7)]
    observances = [obs for p, day in zip(days, dates) for obs in _detect_observances(p, day)]
    return days, observances


# ── Verse Pairing ────────────────────────────────────────────────────

def _build_verse_query(observances: list[Observance], panchang_days: list[DailyPanchang]) -> str:
    """Build a natural-language search query from observances and panchang context."""
    obs_terms = [f"{o.name} {o.deity} {o.description}" for o in observances]
    panchang_terms = [f"{p.tithi} {p.nakshatra}" for p in panchang_days]
    return " ".join(obs_terms + panchang_terms)


def _verse_to_dict(v: Verse) -> dict:
    """Convert a Verse dataclass to the digest-compatible dict format."""
    return {"devanagari": v.devanagari, "transliteration": v.transliteration, "meaning": v.meaning, "source": v.source}


def pair_verse(observances: list[Observance], panchang_days: list[DailyPanchang]) -> tuple[dict | None, dict]:
    """Pick a relevant Sanskrit verse via semantic search, with keyword fallback.

    Returns (verse_dict, search_meta) where search_meta has query, latency_ms, verse_id.
    """
    meta: dict = {"query": "", "latency_ms": 0.0, "verse_id": "none", "verse_source": ""}
    if not observances:
        return None, meta
    query = _build_verse_query(observances, panchang_days)
    meta["query"] = query
    t0 = time.perf_counter()
    results = semantic_search(query, top_k=1) or keyword_search(query, top_k=1)
    meta["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    if not results:
        return None, meta
    meta["verse_id"] = results[0].id
    meta["verse_source"] = results[0].source
    return _verse_to_dict(results[0]), meta


# ── Output ───────────────────────────────────────────────────────────

def format_digest(digest: WeeklyDigest) -> str:
    """Pretty-print the weekly digest."""
    lines = [
        "═══ Vedic Wisdom Weekly ═══",
        f"Week: {digest.week_start} → {digest.week_end}",
        "",
        "📅 Daily Panchangam:",
    ] + [f"  {p.date} ({p.vaara}) | {p.paksha} {p.tithi} | {p.nakshatra} | Sunrise {p.sunrise}" for p in digest.panchang_days]

    lines.append("")
    if digest.observances:
        lines.append("🔔 Observances This Week:")
        lines += [f"  • {o.date} — {o.name} ({o.deity}): {o.description}" for o in digest.observances]
    else:
        lines.append("No major observances this week.")

    if digest.verse:
        lines += [
            "",
            "🙏 Verse of the Week:",
            f"  {digest.verse['devanagari']}",
            f"  {digest.verse['transliteration']}",
            f"  — {digest.verse['meaning']}",
            f"  [{digest.verse.get('source', '')}]",
        ]
    return "\n".join(lines)


def generate_weekly(start: dt.date | None = None) -> str:
    """Entry point — generate this week's notification and log to MLflow."""
    start = start or dt.date.today()
    end = start + dt.timedelta(days=6)
    days, observances = get_week_data(start)
    verse, meta = pair_verse(observances, days)
    digest = WeeklyDigest(week_start=start, week_end=end, panchang_days=days, observances=observances, verse=verse)
    log_notification(
        week=str(start),
        observance_count=len(observances),
        verse_id=meta["verse_id"],
        observance_names=", ".join(o.name for o in observances),
        verse_source=meta["verse_source"],
        search_query=meta["query"],
        search_latency_ms=meta["latency_ms"],
    )
    return format_digest(digest)


if __name__ == "__main__":
    print(generate_weekly())
