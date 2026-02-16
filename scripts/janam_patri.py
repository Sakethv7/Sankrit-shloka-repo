"""Janam patri — birth nakshatra/rashi and shloka recommendations (Hindu way).

Reads birth details from config, uses Swiss Ephemeris for sidereal moon
(Lahiri ayanamsha), maps janma nakshatra to deity themes, and returns
recommended Sanskrit verses.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import swisseph as swe
import yaml

# Panchang nakshatra names
NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

RASHI_NAMES = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena",
]

# Janma nakshatra → search theme for verse (deity / tradition)
NAKSHATRA_THEME = {
    "Ashwini": "healing vitality Ashwini Kumaras",
    "Bharani": "transformation Yama dharma",
    "Krittika": "Agni fire purification",
    "Rohini": "moon devotion beauty",
    "Mrigashira": "Soma moon seeking",
    "Ardra": "Shiva Rudra storm",
    "Punarvasu": "Aditi abundance home",
    "Pushya": "Brihaspati wisdom Jupiter",
    "Ashlesha": "serpent wisdom Naga",
    "Magha": "pitru ancestors royalty",
    "Purva Phalguni": "love devotion Venus",
    "Uttara Phalguni": "grace Aryaman",
    "Hasta": "skill Savitr sun",
    "Chitra": "Vishwakarma creation",
    "Swati": "Vayu wind freedom",
    "Vishakha": "Indra Agni victory",
    "Anuradha": "Mitra friendship devotion",
    "Jyeshtha": "Indra protection elder",
    "Mula": "Nirriti dissolution",
    "Purva Ashadha": "Apah waters",
    "Uttara Ashadha": "Vishvedeva universal",
    "Shravana": "Vishnu listening",
    "Dhanishta": "Vasudeva rhythm",
    "Shatabhisha": "Varuna healing",
    "Purva Bhadrapada": "Aja Ekapada",
    "Uttara Bhadrapada": "Ahir Budhnya",
    "Revati": "Pushan nourishment",
}

NAKSHATRA_LIFESTYLE = {
    "Punarvasu": [
        "Keep mornings uncluttered; begin with a short prayer and fresh air.",
        "Nurture home energy: one small act of care in your living space daily.",
        "Prefer steady routines over sudden lifestyle swings this week.",
    ],
}


@dataclass
class BirthChart:
    janma_nakshatra: str
    rashi: str
    nakshatra_num: int
    rashi_num: int


def _jd_ut(year: int, month: int, day: int, hour: float) -> float:
    """Julian day at given UT (hour as fractional 0-24)."""
    return swe.julday(year, month, day, hour)


def _sidereal_moon_longitude(jd_ut: float) -> float:
    """Moon longitude in sidereal (Lahiri ayanamsha), 0–360."""
    moon_tropical = swe.calc_ut(jd_ut, swe.MOON)[0][0]
    ayan = swe.get_ayanamsa_ut(jd_ut)
    return (moon_tropical - ayan) % 360


def compute_birth_chart(birth_date: str, birth_time: str, tz_offset: float) -> BirthChart:
    """Compute janma nakshatra and rashi from birth date/time (local) and timezone."""
    # Parse date YYYY-MM-DD and time HH:MM
    y, m, d = (int(x) for x in birth_date.split("-"))
    parts = birth_time.replace(":", " ").split()
    h = int(parts[0]) if parts else 0
    minu = int(parts[1]) if len(parts) > 1 else 0
    local_hours = h + minu / 60.0
    ut_hours = (local_hours - tz_offset) % 24
    jd = _jd_ut(y, m, d, ut_hours)
    sid_moon = _sidereal_moon_longitude(jd)
    nakshatra_num = int(sid_moon / (360 / 27)) % 27
    rashi_num = int(sid_moon / 30) % 12
    return BirthChart(
        janma_nakshatra=NAKSHATRA_NAMES[nakshatra_num],
        rashi=RASHI_NAMES[rashi_num],
        nakshatra_num=nakshatra_num,
        rashi_num=rashi_num,
    )


def load_janam_config(config_path: Path) -> dict | None:
    """Load config; return janam_patri section if enabled."""
    if not config_path.exists():
        return None
    cfg = yaml.safe_load(config_path.read_text())
    jp = (cfg or {}).get("janam_patri")
    return jp if (jp and jp.get("enabled")) else None


def recommend_verses(theme: str, top_k: int = 5) -> list:
    """Return recommended verses for a search theme (deity/theme string)."""
    _verse_dir = Path(__file__).resolve().parent.parent / "skills" / "sanskrit-wisdom" / "scripts"
    sys.path.insert(0, str(_verse_dir))
    from verse_search import search
    return search(theme, top_k=top_k)


def run_to_dict(config_path: Path | None = None) -> dict | None:
    """Compute birth chart and recommended verses; return JSON-serializable dict or None if disabled."""
    root = Path(__file__).resolve().parent.parent
    config_path = config_path or root / "config.yaml"
    jp = load_janam_config(config_path)
    if not jp:
        return None

    birth_date = jp.get("birth_date", "1990-01-01")
    birth_time = jp.get("birth_time", "10:30")
    place = jp.get("birth_place", {})
    tz = place.get("tz_offset", -5.0)

    chart = compute_birth_chart(birth_date, birth_time, tz)
    janma_nakshatra = jp.get("janma_nakshatra") or chart.janma_nakshatra
    rashi = jp.get("rashi") or chart.rashi
    theme = NAKSHATRA_THEME.get(janma_nakshatra, f"{janma_nakshatra} devotion dharma")
    verses = recommend_verses(theme, top_k=5)
    lifestyle = NAKSHATRA_LIFESTYLE.get(
        janma_nakshatra,
        [
            "Maintain a steady wake-sleep cycle and keep one daily reflection practice.",
            "Choose sattvic food and avoid over-stimulation in late evenings.",
            "Do one intentional act of service each week.",
        ],
    )

    return {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_place": place.get("city", "Birth place"),
        "janma_nakshatra": janma_nakshatra,
        "rashi": rashi,
        "theme": theme,
        "lifestyle_recommendations": lifestyle,
        "verses": [
            {"devanagari": v.devanagari, "transliteration": v.transliteration, "meaning": v.meaning, "source": v.source}
            for v in verses
        ],
    }


def _strip_diacritics(text: str) -> str:
    """Convert transliteration with diacritics to plain ASCII-style text."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_marks.replace("\n", " ")).strip()


def _clean_meaning(text: str) -> str:
    """Normalize spacing and drop duplicated verse prefixes like '7.3 '."""
    clean = re.sub(r"^\s*\d+\.\d+\s*", "", text or "")
    return re.sub(r"\s+", " ", clean).strip()


def run(config_path: Path | None = None) -> str:
    """Load config, compute birth chart, recommend verses. Returns formatted text."""
    data = run_to_dict(config_path)
    if not data:
        return "Janam patri is disabled or missing in config. Set janam_patri.enabled: true and birth details."

    lines = [
        "Janam Patri",
        f"Birth: {data['birth_date']} {data['birth_time']} ({data['birth_place']})",
        f"Janma Nakshatra: {data['janma_nakshatra']} | Rashi: {data['rashi']}",
        "Recommended verses:",
    ]
    for idx, v in enumerate(data["verses"], start=1):
        lines += [
            f"{idx}. {v['source']}",
            f"   Transliteration: {_strip_diacritics(v['transliteration'])}",
            f"   Meaning: {_clean_meaning(v['meaning'])}",
            "",
        ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(run())
