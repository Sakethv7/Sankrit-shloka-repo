"""Weekly Vedic Guidance — personalized 7-day CLI for Saketh.

Panchangam computed for New Delhi (IST) — the standard reference for
Telugu Vedic calendars. Each day gets:
  - Tithi / nakshatra / yoga / karana
  - Rahu Kalam, Yamagandam, Gulika Kalam, Abhijit Muhurta (all IST)
  - Day score for Punarvasu / Mithuna birth profile
  - Jyotish color + gemstone + vastu tip
  - Devata shloka (keyed to tithi deity)
  - Personal shloka (birth-profile scored, memory-aware, no repeat ≤ 4 weeks)
  - Observance guidance (Ekadashi, Pradosham, Amavasya, etc.)

Memory is stored in dashboard/data/shloka_history.json and evolves
automatically each week so you never get the same shloka twice in a row.

Usage:
    python scripts/weekly_guidance.py
    python scripts/weekly_guidance.py --start-date 2026-04-26
    python scripts/weekly_guidance.py --debug
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import swisseph as swe
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "sanskrit-wisdom" / "scripts"))

from panchang import (
    compute as panchang_compute, DailyPanchang,
    is_ekadashi, is_pradosham, is_amavasya, is_purnima, is_chaturthi,
)
from janam_patri import load_janam_config, compute_birth_chart, BirthChart

# ── Paths ──────────────────────────────────────────────────────────────

HISTORY_PATH = ROOT / "dashboard" / "data" / "shloka_history.json"
VERSES_PATH  = ROOT / "skills" / "sanskrit-wisdom" / "data" / "verses.json"
CONFIG_PATH  = ROOT / "config.yaml"

# ── India reference for panchangam (New Delhi) ────────────────────────

INDIA_LAT, INDIA_LON, IST = 28.6139, 77.2090, 5.5

# ── Jyotish tables ────────────────────────────────────────────────────

VAARA_COLOR = {
    "Ravivara":    {"wear": "Red / Saffron",     "avoid": "Black",        "planet": "Surya (Sun)",         "gem": "Ruby"},
    "Somavara":    {"wear": "White / Cream",      "avoid": "Dark Red",     "planet": "Chandra (Moon)",      "gem": "Pearl"},
    "Mangalavara": {"wear": "Red / Coral",        "avoid": "Green",        "planet": "Mangal (Mars)",       "gem": "Red Coral"},
    "Budhavara":   {"wear": "Green / Emerald",    "avoid": "Red",          "planet": "Budha (Mercury)",     "gem": "Emerald"},
    "Guruvara":    {"wear": "Yellow / Gold",      "avoid": "Black",        "planet": "Guru (Jupiter)",      "gem": "Yellow Sapphire"},
    "Shukravara":  {"wear": "White / Light Pink", "avoid": "Dark colors",  "planet": "Shukra (Venus)",      "gem": "Diamond"},
    "Shanivara":   {"wear": "Black / Dark Blue",  "avoid": "Red",          "planet": "Shani (Saturn)",      "gem": "Blue Sapphire / Iron"},
}

# Vastu: best direction to face / energize, keyed to day planet
VASTU_TIP = {
    "Ravivara":    "Face east for morning prayers. Keep the east wall unobstructed — Surya's energy enters here.",
    "Somavara":    "Northwest is Chandra's zone. Keep it calm and cool. Avoid arguments near the main entrance.",
    "Mangalavara": "South is Mars-ruled. Place a red lamp in the south corner and avoid red in the bedroom today.",
    "Budhavara":   "North is Mercury's direction. Keep study / workspace in the north or northeast quadrant today.",
    "Guruvara":    "Northeast (Ishanya) is Guru's seat. Light a lamp here before 7 AM. Keep the space clear.",
    "Shukravara":  "Southeast (Agneya) is Venus's zone. Fresh flowers in the southeast lift home energy today.",
    "Shanivara":   "West is Shani's direction. Keep it tidy and stable. Avoid starting new construction or moves.",
}

# Muhurta slot offsets (0-indexed from sunrise, slot duration = (sunset−sunrise)/8)
RAHU_SLOT   = {"Ravivara":7,"Somavara":1,"Mangalavara":6,"Budhavara":4,"Guruvara":5,"Shukravara":3,"Shanivara":2}
YAMA_SLOT   = {"Ravivara":4,"Somavara":3,"Mangalavara":2,"Budhavara":1,"Guruvara":0,"Shukravara":6,"Shanivara":5}
GULIKA_SLOT = {"Ravivara":6,"Somavara":5,"Mangalavara":4,"Budhavara":3,"Guruvara":2,"Shukravara":1,"Shanivara":0}

# Day quality for Punarvasu (Jupiter-ruled) + Mithuna (Mercury-ruled)
DAY_QUALITY = {
    "Guruvara":    (5, "Excellent — Jupiter rules Punarvasu. Best day for study, new intentions, and devotion."),
    "Budhavara":   (4, "Very good — Mercury rules Mithuna. Sharp focus; ideal for learning and communication."),
    "Somavara":    (4, "Good — Moon nurtures renewal. Keep the morning devotional; home and relationships thrive."),
    "Shukravara":  (3, "Moderate — Creative flow is strong. Avoid impulsive financial decisions."),
    "Ravivara":    (3, "Moderate — Surya asks for discipline. Start with Gayatri; keep the day structured."),
    "Mangalavara": (2, "Caution — Mars creates friction for Mithuna. Avoid arguments and hasty decisions today."),
    "Shanivara":   (2, "Caution — Saturn tests patience. Slow down, serve quietly, do not cut corners."),
}

# Nakshatra compatibility with Punarvasu janma nakshatra
NAK_COMPAT = {
    "Punarvasu":5, "Pushya":5,
    "Ashlesha":4, "Vishakha":4, "Swati":4,
    "Rohini":3, "Ardra":3, "Hasta":3, "Chitra":3, "Uttara Phalguni":3, "Mrigashira":3, "Revati":3,
    "Bharani":2, "Krittika":2, "Jyeshtha":2, "Mula":2, "Shatabhisha":2, "Dhanishta":2,
}

# Tithi (0-29) → primary deity of the day
TITHI_DEITY = [
    "Agni","Brahma","Gauri","Ganesha","Surya","Kartikeya","Shiva","Durga","Durga","Yama",
    "Vishnu","Vishnu","Shiva","Shiva","Vishnu",
    "Agni","Brahma","Gauri","Ganesha","Surya","Kartikeya","Shiva","Durga","Durga","Yama",
    "Vishnu","Vishnu","Shiva","Shiva","Pitrus",
]

# Deity → verse tags (best-matching tags in corpus)
DEITY_TAGS = {
    "Vishnu":    ["vishnu","ekadashi","sahasranama","bhakti"],
    "Shiva":     ["shiva","pradosham","panchakshari","healing"],
    "Ganesha":   ["ganesha","chaturthi","obstacles"],
    "Surya":     ["surya","gayatri","aditya"],
    "Pitrus":    ["pitru","amavasya","ancestors"],
    "Durga":     ["devi","durga","shakti"],
    "Gauri":     ["devi","parvati","gauri"],
    "Brahma":    ["vedic","brahma","knowledge"],
    "Kartikeya": ["kartikeya","murugan","strength"],
    "Agni":      ["agni","fire","purification"],
    "Yama":      ["dharma","ancestors","yama"],
    "Krishna":   ["vishnu","krishna","devotion"],
    "Saraswati": ["saraswati","knowledge","learning"],
}

# Observance guidance
OBS_PRACTICE = {
    "Ekadashi":  "Fast (avoid grains). Recite Vishnu Sahasranama or Om Namo Narayanaya 108×. Read a chapter of Gita. Avoid late-night activities.",
    "Pradosham": "Twilight puja (4:30–6 PM IST). Recite Om Namah Shivaya 108×. Offer milk or bilva leaves if possible. Light a lamp facing west.",
    "Amavasya":  "Perform pitru tarpana — face south and offer sesame + water remembering ancestors. Light a lamp at dusk. Donate food.",
    "Purnima":   "Light 12 lamps. Recite Vishnu Sahasranama. Donate food or clothes. Moon gazing at night is auspicious.",
    "Chaturthi": "Fast until moonrise (Sankashti Chaturthi). Recite Ganesha shloka 21×. Offer durva grass. Meditate on obstacle removal.",
}


@dataclass
class DayResult:
    date: dt.date
    panchang: DailyPanchang
    observance: str
    day_score: int
    day_quality: str
    nak_compat: int
    sunrise: str
    sunset: str
    rahu: str
    yamagandam: str
    gulika: str
    abhijit: str
    color: dict
    deity_of_day: str
    devata_shloka: dict | None
    personal_shloka: dict | None
    vastu_tip: str
    practice: str


# ── I/O helpers ───────────────────────────────────────────────────────

def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def load_verses() -> list[dict]:
    return json.loads(VERSES_PATH.read_text())


def load_history() -> dict:
    if not HISTORY_PATH.exists():
        return {"last_updated": "", "weekly": {}, "daily_devata": {}}
    return json.loads(HISTORY_PATH.read_text())


def save_history(h: dict) -> None:
    HISTORY_PATH.write_text(json.dumps(h, indent=2, ensure_ascii=False))


# ── Astronomy helpers (IST / New Delhi) ───────────────────────────────

def _sunset_jd(jd: float) -> float:
    """Julian Day of sunset at New Delhi."""
    result = swe.rise_trans(jd, swe.SUN, 2, (INDIA_LON, INDIA_LAT, 0.0))
    return result[1][0]


def _jd_to_ist(jd: float) -> str:
    """Convert a Julian Day (UT) to HH:MM IST string."""
    ut_h = (jd % 1 - 0.5) * 24
    local = (ut_h + IST) % 24
    return f"{int(local):02d}:{int((local % 1) * 60):02d}"


def _slot_window(base_jd: float, slot: int, slot_dur: float) -> str:
    """Return 'HH:MM – HH:MM IST' for a muhurta slot."""
    start = _jd_to_ist(base_jd + slot * slot_dur)
    end   = _jd_to_ist(base_jd + (slot + 1) * slot_dur)
    return f"{start} – {end} IST"


def get_muhurtas(date: dt.date, vaara: str) -> dict:
    """Compute Rahu Kalam, Yamagandam, Gulika Kalam, Abhijit in IST."""
    jd = swe.julday(date.year, date.month, date.day, 0.0)
    sr_jd = swe.rise_trans(jd, swe.SUN, 1, (INDIA_LON, INDIA_LAT, 0.0))[1][0]
    ss_jd = _sunset_jd(jd)
    slot  = (ss_jd - sr_jd) / 8          # duration of one muhurta slot in JD
    noon  = (sr_jd + ss_jd) / 2
    return {
        "sunrise":  _jd_to_ist(sr_jd),
        "sunset":   _jd_to_ist(ss_jd),
        "rahu":     _slot_window(sr_jd, RAHU_SLOT[vaara],   slot),
        "yamagandam": _slot_window(sr_jd, YAMA_SLOT[vaara], slot),
        "gulika":   _slot_window(sr_jd, GULIKA_SLOT[vaara], slot),
        "abhijit":  f"{_jd_to_ist(noon - 1/48)} – {_jd_to_ist(noon + 1/48)} IST",
    }


# ── Observance + scoring ──────────────────────────────────────────────

def detect_observance(p: DailyPanchang) -> str:
    if is_ekadashi(p):   return "Ekadashi"
    if is_pradosham(p):  return "Pradosham"
    if is_amavasya(p):   return "Amavasya"
    if is_purnima(p):    return "Purnima"
    if is_chaturthi(p):  return "Chaturthi"
    return ""


def score_day(p: DailyPanchang, chart: BirthChart) -> tuple[int, str]:
    base_score, base_msg = DAY_QUALITY.get(p.vaara, (3, "Neutral day. Steady effort is best."))
    nak_boost  = 1 if NAK_COMPAT.get(p.nakshatra, 2) >= 4 else 0
    observance = detect_observance(p)
    obs_boost  = 1 if observance else 0
    obs_suffix = f" ✦ {observance} elevates the day." if observance else ""
    return min(5, base_score + nak_boost + obs_boost), base_msg + obs_suffix


# ── Verse selection ───────────────────────────────────────────────────

def _recent_ids(history: dict, weeks: int = 4) -> set[str]:
    """IDs used in the last `weeks` weekly cycles."""
    all_ids: set[str] = set()
    for v in history.get("weekly", {}).values():
        all_ids.update(v.get("ids", []))
    # Also include last N daily devata entries
    daily = list(history.get("daily_devata", {}).values())
    all_ids.update(daily[-weeks * 7:])
    return all_ids


def _score_verse(v: dict, want_tags: list[str], birth_tags: list[str], used: set[str]) -> float:
    tags = set(v.get("tags", []) + v.get("use_cases", []) + v.get("observance_tags", []) + v.get("birth_tags", []))
    obs_match    = sum(3 for t in want_tags if t in tags)
    birth_match  = sum(2 for t in birth_tags if t in tags)
    smarta_bonus = 1 if v.get("sampradaya", "").lower() in ("smarta", "vedanta/gita", "smarta/pitru") else 0
    generic_pen  = -2 if "daily" in tags and not any(t in tags for t in want_tags) else 0
    recent_pen   = -4 if v["id"] in used else 0
    return obs_match + birth_match + smarta_bonus + generic_pen + recent_pen


def pick_shloka(verses: list[dict], want_tags: list[str], birth_tags: list[str], used: set[str]) -> dict | None:
    """Pick the best-scoring verse; return None if corpus is empty."""
    scored = sorted(verses, key=lambda v: _score_verse(v, want_tags, birth_tags, used), reverse=True)
    return scored[0] if scored else None


def pick_devata_shloka(p: DailyPanchang, verses: list[dict], history: dict) -> dict | None:
    deity = TITHI_DEITY[p.tithi_num]
    want_tags = DEITY_TAGS.get(deity, [deity.lower()])
    used = set(history.get("daily_devata", {}).values())
    return pick_shloka(verses, want_tags, [], used)


def pick_personal_shloka(p: DailyPanchang, chart: BirthChart, verses: list[dict],
                          history: dict, weekly_used: list[str],
                          exclude: set[str] | None = None) -> dict | None:
    observance = detect_observance(p)
    obs_tags   = DEITY_TAGS.get(TITHI_DEITY[p.tithi_num], []) if observance else []
    birth_tags = ["punarvasu", "mithuna", "smarta", "vishnu"]
    # Hard-exclude same-week used + devata — penalize only recent history
    hard_excl  = set(weekly_used) | (exclude or set())
    soft_used  = _recent_ids(history) - hard_excl
    pool = [v for v in verses if v["id"] not in hard_excl]
    return pick_shloka(pool, obs_tags, birth_tags, soft_used)


# ── Day assembly ──────────────────────────────────────────────────────

def build_day(date: dt.date, chart: BirthChart, verses: list[dict],
              history: dict, weekly_used: list[str]) -> DayResult:
    p          = panchang_compute(date, lat=INDIA_LAT, lon=INDIA_LON, tz=IST)
    muhurtas   = get_muhurtas(date, p.vaara)
    observance = detect_observance(p)
    day_score, day_quality = score_day(p, chart)
    nak_compat = NAK_COMPAT.get(p.nakshatra, 2)
    color      = VAARA_COLOR[p.vaara]
    deity      = TITHI_DEITY[p.tithi_num]
    devata_s   = pick_devata_shloka(p, verses, history)
    devata_excl = {devata_s["id"]} if devata_s else set()
    personal_s = pick_personal_shloka(p, chart, verses, history, weekly_used, exclude=devata_excl)
    practice   = OBS_PRACTICE.get(observance, _default_practice(p.vaara, day_score))
    return DayResult(
        date=date, panchang=p, observance=observance,
        day_score=day_score, day_quality=day_quality, nak_compat=nak_compat,
        sunrise=muhurtas["sunrise"], sunset=muhurtas["sunset"],
        rahu=muhurtas["rahu"], yamagandam=muhurtas["yamagandam"],
        gulika=muhurtas["gulika"], abhijit=muhurtas["abhijit"],
        color=color, deity_of_day=deity,
        devata_shloka=devata_s, personal_shloka=personal_s,
        vastu_tip=VASTU_TIP[p.vaara], practice=practice,
    )


def _default_practice(vaara: str, score: int) -> str:
    practices = {
        "Guruvara":    "Recite Om Namo Bhagavate Vasudevaya 108×. Offer yellow flowers if possible. Excellent for study.",
        "Budhavara":   "Recite Saraswati Vandana. Focus on learning or writing. Green vegetables are favored today.",
        "Somavara":    "Recite Om Namah Shivaya 108×. Offer white flowers. Keep the morning calm and meditative.",
        "Shukravara":  "Recite Lakshmi Ashtakam or Devi mantra. Keep the home clean and fragrant.",
        "Ravivara":    "Recite Gayatri Mantra 108× at sunrise. Offer water to the Sun (Surya Arghya). Eat lightly.",
        "Mangalavara": "Recite Ganesha shloka before any important work. Avoid starting new ventures. Be patient.",
        "Shanivara":   "Recite Hanuman Chalisa or a Shiva mantra. Donate sesame / mustard oil. Serve someone in need.",
    }
    return practices.get(vaara, "Maintain steady practice. Recite your primary mantra 108×.")


# ── Formatting ────────────────────────────────────────────────────────

def _stars(n: int, max_n: int = 5) -> str:
    return "★" * n + "☆" * (max_n - n)


def _nak_compat_label(n: int) -> str:
    return {5: "Excellent", 4: "Good", 3: "Moderate", 2: "Challenging"}.get(n, "Neutral")


def _fmt_shloka(label: str, shloka: dict | None) -> str:
    if not shloka:
        return f"  [{label}: no verse matched today]\n"
    lines = [f"  {label} — {shloka['source']}",
             f"    {shloka['devanagari']}",
             f"    {shloka['transliteration']}",
             f"    {shloka['meaning']}"]
    return "\n".join(lines) + "\n"


def fmt_day(day: DayResult, idx: int, debug: bool = False) -> str:
    p       = day.panchang
    en_day  = {"Ravivara":"Sunday","Somavara":"Monday","Mangalavara":"Tuesday",
               "Budhavara":"Wednesday","Guruvara":"Thursday","Shukravara":"Friday","Shanivara":"Saturday"}
    vaara   = en_day.get(p.vaara, p.vaara)
    obs_str = f" ✦ {day.observance.upper()}" if day.observance else ""
    header  = f"DAY {idx} — {vaara.upper()}, {day.date.strftime('%b %d')}{obs_str}"
    sep     = "─" * len(header)

    panch = (f"  Tithi:     {p.paksha} {p.tithi}  |  Nakshatra: {p.nakshatra}  |  Yoga: {p.yoga}\n"
             f"  Vaara:     {vaara} ({p.vaara})  |  Karana: {p.karana}")

    timings = (f"  Sunrise:          {day.sunrise} IST  |  Sunset: {day.sunset} IST\n"
               f"  Rahu Kalam:       {day.rahu}  ⚠ avoid new beginnings\n"
               f"  Yamagandam:       {day.yamagandam}  ⚠ avoid travel/decisions\n"
               f"  Gulika Kalam:     {day.gulika}\n"
               f"  Abhijit Muhurta:  {day.abhijit}  ✓ auspicious for important work")

    quality = (f"  {_stars(day.day_score)} ({day.day_score}/5)  {day.day_quality}\n"
               f"  Nakshatra {p.nakshatra}: {_stars(day.nak_compat)} — {_nak_compat_label(day.nak_compat)} for Punarvasu")

    color_s = (f"  Wear:      {day.color['wear']}\n"
               f"  Avoid:     {day.color['avoid']}\n"
               f"  Planet:    {day.color['planet']}  |  Gemstone: {day.color['gem']}")

    devata_str   = _fmt_shloka(f"Devata Shloka (Deity: {day.deity_of_day})", day.devata_shloka)
    personal_str = _fmt_shloka("Personal Shloka", day.personal_shloka)

    practice_label = f"Practice{' — ' + day.observance if day.observance else ''}"
    blocks = [
        sep, header, sep,
        "Panchangam (IST, New Delhi reference)\n" + panch,
        "Timings (IST)\n" + timings,
        f"Day Quality\n{quality}",
        f"Color & Vastu\n{color_s}\n  Tip: {day.vastu_tip}",
        devata_str.rstrip(),
        personal_str.rstrip(),
        f"{practice_label}\n  {day.practice}",
        "",
    ]
    return "\n\n".join(blocks)


def fmt_week_header(days: list[DayResult], chart: BirthChart) -> str:
    start, end = days[0].date, days[-1].date
    obs_days   = [(d.date.strftime("%b %d"), d.observance) for d in days if d.observance]
    best       = [d for d in days if d.day_score == 5]
    caution    = [d for d in days if d.day_score <= 2]
    en_day = {"Ravivara":"Sunday","Somavara":"Monday","Mangalavara":"Tuesday",
              "Budhavara":"Wednesday","Guruvara":"Thursday","Shukravara":"Friday","Shanivara":"Saturday"}

    header = [
        "═" * 62,
        "  VEDIC WEEKLY GUIDANCE — Saketh",
        f"  Week of {start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}",
        f"  Janma Nakshatra: {chart.janma_nakshatra}  |  Rashi: {chart.rashi}",
        f"  Tradition: Golconda Vyapari Niyogi Brahmin (Smarta)",
        "═" * 62,
        "",
        "WEEK OVERVIEW",
        "─" * 40,
    ]
    if obs_days:
        header.append("Observances:")
        header += [f"  ✦ {obs} — {date}" for date, obs in obs_days]
    if best:
        names = ", ".join(f"{en_day[d.panchang.vaara]} {d.date.strftime('%b %d')}" for d in best)
        header.append(f"Best days:      {names}")
    if caution:
        names = ", ".join(f"{en_day[d.panchang.vaara]} {d.date.strftime('%b %d')}" for d in caution)
        header.append(f"Caution days:   {names}")
    header.append("")
    return "\n".join(header)


# ── History update ─────────────────────────────────────────────────────

def update_history(history: dict, days: list[DayResult], week_key: str) -> None:
    """Record used shlokas in history so future weeks rotate them."""
    weekly_ids = list({d.devata_shloka["id"] for d in days if d.devata_shloka}
                      | {d.personal_shloka["id"] for d in days if d.personal_shloka})
    history.setdefault("weekly", {})[week_key] = {"ids": weekly_ids}
    daily = history.setdefault("daily_devata", {})
    for d in days:
        if d.devata_shloka:
            daily[str(d.date)] = d.devata_shloka["id"]
    history["last_updated"] = str(dt.date.today())


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Vedic weekly guidance for Saketh")
    parser.add_argument("--start-date", help="Week start date YYYY-MM-DD (default: today)")
    parser.add_argument("--debug", action="store_true", help="Show verse scores")
    args = parser.parse_args()

    start = (dt.date.fromisoformat(args.start_date) if args.start_date
             else dt.date.today())

    cfg    = load_config()
    jp     = load_janam_config(CONFIG_PATH)
    verses = load_verses()

    if jp:
        place = jp.get("birth_place", {})
        chart = compute_birth_chart(jp["birth_date"], jp["birth_time"], place.get("tz_offset", 5.5))
        chart = BirthChart(
            janma_nakshatra=jp.get("janma_nakshatra") or chart.janma_nakshatra,
            rashi=jp.get("rashi") or chart.rashi,
            nakshatra_num=chart.nakshatra_num,
            rashi_num=chart.rashi_num,
        )
    else:
        print("Error: janam_patri not configured in config.yaml", file=sys.stderr)
        sys.exit(1)

    history    = load_history()
    week_key   = start.strftime("%Y-W%W")
    weekly_used: list[str] = []

    days = []
    for offset in range(7):
        day = build_day(start + dt.timedelta(days=offset), chart, verses, history, weekly_used)
        if day.personal_shloka:
            weekly_used.append(day.personal_shloka["id"])
        days.append(day)

    print(fmt_week_header(days, chart))
    for i, day in enumerate(days, 1):
        print(fmt_day(day, i, debug=args.debug))

    update_history(history, days, week_key)
    save_history(history)
    print(f"\n[Memory updated: {HISTORY_PATH}]")


if __name__ == "__main__":
    main()
