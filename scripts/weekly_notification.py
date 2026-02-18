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


# Tithi → search theme for shloka (Hindu calendar; EST already in panchang)
TITHI_QUERY_MAP = {
    "Pratipada": "Ganesha beginning auspicious",
    "Chaturthi": "Ganesha chaturthi obstacles",
    "Ekadashi": "Vishnu ekadashi devotion",
    "Trayodashi": "Shiva pradosham",
    "Amavasya": "pitru ancestors amavasya tarpanam",
    "Purnima": "full moon devotion",
    "Dwadashi": "Vishnu devotion",
}

@dataclass
class DailyVerse:
    date: dt.date
    tithi: str
    paksha: str
    verse: dict | None


@dataclass
class WeeklyDigest:
    week_start: dt.date
    week_end: dt.date
    panchang_days: list[DailyPanchang] = field(default_factory=list)
    observances: list[Observance] = field(default_factory=list)
    verse: dict | None = None
    daily_verses: list[DailyVerse] = field(default_factory=list)
    lifestyle_recommendations: list[str] = field(default_factory=list)


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
    return {
        "devanagari": v.devanagari,
        "transliteration": v.transliteration,
        "meaning": v.meaning,
        "source": v.source,
        "sampradaya": v.sampradaya,
        "deity": v.deity,
        "script": v.script,
        "category": v.category,
    }


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


def _query_for_tithi(p: DailyPanchang, observance_for_day: list[Observance]) -> str:
    """Build search query for this day from tithi and any observance (EST day already in p)."""
    if observance_for_day:
        return " ".join([f"{o.name} {o.deity} {o.description}" for o in observance_for_day])
    return TITHI_QUERY_MAP.get(p.tithi, f"{p.tithi} {p.nakshatra} dharma")


def get_daily_verses(panchang_days: list[DailyPanchang], dates: list[dt.date], observances: list[Observance]) -> list[DailyVerse]:
    """One shloka per day by tithi (and observance) for the week — EST dates."""
    obs_by_date: dict[dt.date, list[Observance]] = {}
    for o in observances:
        obs_by_date.setdefault(o.date, []).append(o)
    out = []
    for p, day in zip(panchang_days, dates):
        obs = obs_by_date.get(day, [])
        query = _query_for_tithi(p, obs)
        results = semantic_search(query, top_k=1) or keyword_search(query, top_k=1)
        verse = _verse_to_dict(results[0]) if results else None
        out.append(DailyVerse(date=p.date, tithi=p.tithi, paksha=p.paksha, verse=verse))
    return out


def build_lifestyle_recommendations(
    panchang_days: list[DailyPanchang],
    observances: list[Observance],
) -> list[str]:
    """Generate concise, practical weekly lifestyle recommendations."""
    recs: list[str] = []
    obs_names = {o.name for o in observances}
    tithis = {p.tithi for p in panchang_days}

    if "Amavasya" in obs_names:
        recs.append("Amavasya week: spend time in quiet reflection and gratitude for ancestors.")
    if "Ekadashi" in obs_names:
        recs.append("Ekadashi: keep meals light and sattvic, with extra hydration and simple japa.")
    if "Sankashti Chaturthi" in obs_names or "Chaturthi" in tithis:
        recs.append("Chaturthi energy: clear one pending task and remove one source of clutter.")
    if any(p.vaara == "Somavara" for p in panchang_days):
        recs.append("Somavara: start the week with a short sankalpa and 10 minutes of silence.")
    if any(p.vaara == "Guruvara" for p in panchang_days):
        recs.append("Guruvara: reserve time for study, guidance, or one act of teaching.")

    recs.append("Daily anchor: avoid digital overload for one focused hour after sunrise.")
    return recs[:5]


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

    if digest.daily_verses:
        lines.append("")
        lines.append("📿 Shloka by Tithi (this week, EST):")
        for dv in digest.daily_verses:
            tithi_line = f"  {dv.date} ({dv.paksha} {dv.tithi})"
            if dv.verse:
                lines.append(tithi_line)
                lines.append(f"    {dv.verse['devanagari']}")
                lines.append(f"    {dv.verse['transliteration']}")
                lines.append(f"    — {dv.verse['meaning']} [{dv.verse.get('source', '')}]")
            else:
                lines.append(f"{tithi_line} — (no verse matched)")

    if digest.verse:
        lines += [
            "",
            "🙏 Verse of the Week:",
            f"  {digest.verse['devanagari']}",
            f"  {digest.verse['transliteration']}",
            f"  — {digest.verse['meaning']}",
            f"  [{digest.verse.get('source', '')}]",
        ]

    if digest.lifestyle_recommendations:
        lines += ["", "🌿 Lifestyle recommendations:"]
        lines += [f"  • {r}" for r in digest.lifestyle_recommendations]
    return "\n".join(lines)


def build_digest(start: dt.date | None = None) -> tuple[WeeklyDigest, dict]:
    """Build the weekly digest (no MLflow log). Returns (digest, search_meta)."""
    start = start or dt.date.today()
    end = start + dt.timedelta(days=6)
    dates = [start + dt.timedelta(days=i) for i in range(7)]
    days, observances = get_week_data(start)
    verse, meta = pair_verse(observances, days)
    daily_verses = get_daily_verses(days, dates, observances)
    lifestyle_recs = build_lifestyle_recommendations(days, observances)
    digest = WeeklyDigest(
        week_start=start, week_end=end, panchang_days=days, observances=observances,
        verse=verse, daily_verses=daily_verses, lifestyle_recommendations=lifestyle_recs,
    )
    return digest, meta


def digest_to_dict(digest: WeeklyDigest) -> dict:
    """Serialize digest to JSON-serializable dict for dashboard."""
    def day_dict(p: DailyPanchang) -> dict:
        return {"date": str(p.date), "vaara": p.vaara, "tithi": p.tithi, "paksha": p.paksha, "nakshatra": p.nakshatra, "sunrise": p.sunrise}

    obs_list = [{"date": str(o.date), "name": o.name, "deity": o.deity, "description": o.description} for o in digest.observances]
    daily = [{"date": str(dv.date), "tithi": dv.tithi, "paksha": dv.paksha, "verse": dv.verse} for dv in digest.daily_verses]
    return {
        "week_start": str(digest.week_start),
        "week_end": str(digest.week_end),
        "panchang_days": [day_dict(p) for p in digest.panchang_days],
        "observances": obs_list,
        "daily_verses": daily,
        "verse_of_week": digest.verse,
        "lifestyle_recommendations": digest.lifestyle_recommendations,
    }


def generate_weekly(start: dt.date | None = None) -> str:
    """Entry point — generate this week's notification and log to MLflow."""
    digest, meta = build_digest(start)
    digest_text = format_digest(digest)
    log_notification(
        week=str(digest.week_start),
        observance_count=len(digest.observances),
        verse_id=meta.get("verse_id", "none"),
        observance_names=", ".join(o.name for o in digest.observances),
        verse_source=meta.get("verse_source", ""),
        search_query=meta.get("query", ""),
        search_latency_ms=meta.get("latency_ms", 0),
        digest_text=digest_text,
    )
    return digest_text


if __name__ == "__main__":
    print(generate_weekly())
