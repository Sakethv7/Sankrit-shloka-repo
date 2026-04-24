# Architecture — Vedic Wisdom Weekly

This document describes the technical design of the system: data flow, component responsibilities, algorithms, data models, and the reasoning behind key decisions.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        weekly_guidance.py                           │
│  (primary CLI — 7-day personalized output to stdout)               │
└────────────────────────┬────────────────────────────────────────────┘
                         │ reads
          ┌──────────────┼────────────────────────────┐
          ▼              ▼                            ▼
   config.yaml     verses.json              shloka_history.json
   (birth profile, (15 curated verses,      (memory: shlokas used
    observances,    fully tagged)            per week — auto-updated)
    feature flags)
          │
          ▼
   ┌─────────────────────────────────┐
   │        panchang.py              │  ─── Swiss Ephemeris (pyswisseph)
   │  tithi · nakshatra · yoga       │       local practice coords/timezone
   │  karana · sunrise · sunset      │
   └─────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────┐
   │       janam_patri.py            │  ─── sidereal Moon longitude
   │  BirthChart: nakshatra, rashi   │       Lahiri ayanamsha
   │  nakshatra_num, rashi_num       │
   └─────────────────────────────────┘

Legend:
  weekly_guidance.py  = primary daily driver
  weekly_notification.py = legacy compatibility path
  verse_search.py     = optional Qdrant semantic search layer
  tracker.py          = optional MLflow logging layer
```

---

## Data Flow — `weekly_guidance.py`

```
1. Load config.yaml
        │
        ▼
2. Compute BirthChart (janam_patri.py)
   → sidereal Moon longitude at birth → nakshatra + rashi
        │
        ▼
3. Resolve practice_location
   → local latitude, longitude, and timezone for observance timing
        │
        ▼
4. For each of 7 days starting from --start-date (default: today):
        │
        ├─ 4a. compute(date, lat=practice.lat, lon=practice.lon, tz=date_offset)  [panchang.py]
        │       tithi, nakshatra, yoga, karana, vaara, sunrise
        │
        ├─ 4b. get_muhurtas(date, vaara, practice_location)
        │       sunrise_jd, sunset_jd → slot_duration = (sunset-sunrise)/8
        │       Rahu/Yamagandam/Gulika = sunrise + offset*slot
        │       Abhijit = solar_noon ± 30 min
        │
        ├─ 4c. score_day(panchang, chart)
        │       base = DAY_QUALITY[vaara]  (1–5)
        │       + 1 if nakshatra_compat >= 4
        │       + 1 if observance present
        │       → capped at 5
        │
        ├─ 4d. pick_devata_shloka(panchang, verses, history)
        │       deity = TITHI_DEITY[tithi_num]
        │       want_tags = DEITY_TAGS[deity]
        │       score all verses → pick highest
        │
        ├─ 4e. pick_personal_shloka(panchang, chart, verses, history, weekly_used)
        │       hard_excl = weekly_used (this week) + devata_shloka_id
        │       soft_used = _recent_ids(history) - hard_excl
        │       score remaining verses → pick highest
        │
        └─ 4f. assemble DayResult dataclass
                │
                ▼
5. format and print 7-day report to stdout
        │
        ▼
6. optionally update_history() → save shloka_history.json
   live current-week runs write memory; --start-date backtests do not unless --write-history is passed
```

---

## Components

### `scripts/panchang.py` — Panchangam Engine

Computes the five limbs (pañcāṅga) of the Hindu calendar for any date and location using **pyswisseph** (Swiss Ephemeris C library wrapper).

**Key calculations:**
- **Tithi** — lunar day. `diff = (moon_lon - sun_lon) % 360 / 12` → 0–29
- **Nakshatra** — Moon's constellation. Sidereal Moon longitude (Lahiri ayanamsha applied) / (360/27) → 0–26
- **Yoga** — (sidereal Sun + Moon) % 360 / (360/27) → 0–26
- **Karana** — half-tithi. Maps 60 karanas to 11 named ones; fixed karanas (Shakuni, Chatushpada, Nagava, Kimstughna) handled explicitly
- **Vaara** — weekday from Julian Day Number: `int((jd + 1.5) % 7)`
- **Sunrise** — `swe.rise_trans(jd, swe.SUN, rsmi=1, geopos)` → JD of sunrise; converted to local HH:MM

**Reference coordinates:** `weekly_guidance.py` passes the configured `practice_location` into this engine. The default is New Jersey with `America/New_York`, so sunrise-based observances and muhurta windows match where the practice happens.

**Why local?** The rule base is Indic / Telugu / Smarta, but the civil day, sunrise, sunset, Rahu Kalam, Pradosham, and fasting windows should be local for the person practicing.

---

### `scripts/janam_patri.py` — Birth Chart

Computes janma nakshatra and rashi from birth date/time/location.

**Method:**
1. Convert local birth time to UT: `ut_hours = (local_h - tz_offset) % 24`
2. Compute Julian Day at birth
3. Get tropical Moon longitude via `swe.calc_ut(jd, swe.MOON)`
4. Apply Lahiri ayanamsha: `sidereal = (tropical - ayan) % 360`
5. Nakshatra: `int(sidereal / (360/27)) % 27`
6. Rashi: `int(sidereal / 30) % 12`

**Known values from config** (Saketh): Punarvasu (nakshatra 6), Mithuna/Gemini (rashi 2). These are used directly when set in `config.yaml`; the computation runs as a cross-check.

---

### `scripts/weekly_guidance.py` — Primary CLI

The orchestration layer. Owns all jyotish lookup tables and scoring logic. No external API calls; runs purely on local data.

**Key data structures:**

```python
@dataclass
class DayResult:
    date: dt.date
    panchang: DailyPanchang    # tithi, nak, yoga, karana, vaara, sunrise
    observance: str            # "Ekadashi" | "Pradosham" | "" | ...
    day_score: int             # 1–5
    day_quality: str           # human-readable reason
    nak_compat: int            # 1–5, Punarvasu compatibility
    sunrise: str               # "HH:MM TZ"
    sunset: str
    rahu: str                  # "HH:MM – HH:MM TZ"
    yamagandam: str
    gulika: str
    abhijit: str
    color: dict                # {wear, avoid, planet, gem}
    deity_of_day: str          # tithi deity
    devata_shloka: dict | None
    personal_shloka: dict | None
    vastu_tip: str
    practice: str
```

---

### Muhurta Algorithm

Rahu Kalam, Yamagandam, and Gulika Kalam divide the day into 8 equal slots between sunrise and sunset. Each weekday uses a fixed slot number (0-indexed from sunrise):

| Vaara | Rahu slot | Yama slot | Gulika slot |
|-------|-----------|-----------|-------------|
| Ravivara (Sun)  | 7 | 4 | 6 |
| Somavara (Mon)  | 1 | 3 | 5 |
| Mangalavara (Tue) | 6 | 2 | 4 |
| Budhavara (Wed)  | 4 | 1 | 3 |
| Guruvara (Thu)   | 5 | 0 | 2 |
| Shukravara (Fri) | 3 | 6 | 1 |
| Shanivara (Sat)  | 2 | 5 | 0 |

```
slot_duration = (sunset_jd - sunrise_jd) / 8
rahu_start    = sunrise_jd + RAHU_SLOT[vaara] * slot_duration
rahu_end      = rahu_start + slot_duration
```

**Abhijit Muhurta** (most auspicious window):
```
solar_noon = (sunrise_jd + sunset_jd) / 2
abhijit    = [noon - 1/48 day, noon + 1/48 day]   # ±30 minutes
```

All times are converted to the configured local timezone with `zoneinfo`, so DST is handled by date.

---

### Day Scoring for Punarvasu / Mithuna

Base scores by weekday planet:

| Vaara | Score | Reason |
|-------|-------|--------|
| Guruvara (Thu) | 5 | Jupiter rules Punarvasu nakshatra |
| Budhavara (Wed) | 4 | Mercury rules Mithuna rashi |
| Somavara (Mon) | 4 | Moon is nurturing; Punarvasu's deity Aditi is lunar |
| Shukravara (Fri) | 3 | Moderate — creative but financially risky |
| Ravivara (Sun) | 3 | Moderate — disciplined effort works |
| Mangalavara (Tue) | 2 | Mars creates friction for air-sign Mithuna |
| Shanivara (Sat) | 2 | Saturn tests patience; slow movement favored |

Boosts applied after base:
- `+1` if today's nakshatra is highly compatible with Punarvasu (Pushya=5, Ashlesha=4, Vishakha=4, Swati=4)
- `+1` if an observance falls today (Ekadashi, Pradosham, Amavasya, Purnima, Chaturthi)
- Capped at 5

---

### Verse Scoring Algorithm

Called twice per day — once for the devata shloka, once for the personal shloka.

```
score(verse, want_tags, birth_tags, soft_used_set) =
    sum(3 for t in want_tags  if t in verse_all_tags)   # observance/deity match
  + sum(2 for t in birth_tags if t in verse_all_tags)   # birth profile match
  + 1  if sampradaya in ("Smarta", "Vedanta/Gita", "Smarta/Pitru")
  - 2  if "daily" in tags AND no want_tag matched       # generic verse penalty
  - 4  if verse.id in soft_used_set                     # recent history penalty
```

Where `verse_all_tags = tags + use_cases + observance_tags + birth_tags` (all four fields unioned).

**Devata shloka** — `want_tags = DEITY_TAGS[tithi_deity]`, `birth_tags = []`, `soft_used = daily_devata history`

**Personal shloka** — `want_tags = DEITY_TAGS[tithi_deity] if observance else []`, `birth_tags = ["punarvasu","mithuna","smarta","vishnu"]`, plus hard exclusions (see Memory below)

---

### Memory System

File: `dashboard/data/shloka_history.json`

```json
{
  "last_updated": "2026-04-23",
  "weekly": {
    "2026-W16": { "ids": ["bg-9.22", "vs-1", "shiva-panchakshari", ...] }
  },
  "daily_devata": {
    "2026-04-23": "shiva-mahamrityunjaya",
    "2026-04-24": "devi-stuti",
    ...
  }
}
```

**Two-tier exclusion for personal shloka:**

| Tier | Scope | Effect |
|------|-------|--------|
| **Hard exclude** | Same-week `weekly_used` list + today's devata shloka | Completely removed from candidate pool |
| **Soft penalty** | All IDs from `weekly` history + recent `daily_devata` entries | `-4` score penalty; can still win if corpus is depleted |

This guarantees 7 unique personal shlokas per run while the corpus is large enough. Over recent weeks, shlokas naturally rotate: a heavily used verse is penalized until the penalty cannot overcome fresh alternatives.

---

### `skills/sanskrit-wisdom/scripts/verse_search.py` — RAG Layer

Two search modes, tried in order:

**1. Semantic search (Qdrant)**
- Encode query with `paraphrase-multilingual-MiniLM-L12-v2` (multilingual sentence transformer)
- Query on-disk Qdrant collection (`skills/sanskrit-wisdom/data/qdrant_store/`)
- Returns top-k Verse objects from payload

**2. Keyword fallback**
- Counts how many of the verse's `tags` appear in the lowercase query
- Adds 1 bonus if query appears in `meaning` text
- Sorts by score, returns top-k with score > 0

`weekly_guidance.py` does **not** use `verse_search.py` — it loads and scores verses directly. The search script is a standalone tool for exploration and used by the legacy `janam_patri.py` recommendation path.

---

### `skills/ml-experiment/tracker.py` — MLflow Tracking

Wraps MLflow runs with a graceful availability check. On first call, it attempts `mlflow.set_tracking_uri()` and sets a module-level `_mlflow_available` flag. If MLflow is unreachable (no server, no SQLite file, wrong URI), all subsequent calls are no-ops — the core CLI never fails due to a missing tracking dependency.

Tracked per weekly notification run:
- Params: `week`, `verse_id`, `verse_source`, `observances`, `search_query`
- Metrics: `observance_count`, `search_latency_ms`, `corpus_size`
- Artifacts: `weekly_digest.txt` (full digest text)

---

## GitHub Actions CI Pipeline

File: `.github/workflows/weekly-digest.yml`
Schedule: **every Sunday 13:00 UTC (8 AM Eastern during standard time)**

```
checkout
    │
    ▼
install requirements.txt
    │
    ▼
verify MLflow reachable (warning only — never fails the run)
    │
    ▼
weekly_guidance.py --write-history → stdout guidance + shloka memory
    │
    ▼
slack_notify.py → POST to Slack webhook
    │
    ▼
export_mlflow_runs.py → dashboard/data/recommendations.json
export_to_sqlite.py   → dashboard/data/vedic_wisdom.db
    │
    ▼
git commit + push dashboard/data/  (if changed)
    │
    ▼
deploy-dashboard job: upload dashboard/ → GitHub Pages
```

**Note:** `weekly_guidance.py` is the canonical engine. Slack and dashboard exports read from that path; `weekly_notification.py` remains as an older compatibility/MLflow-oriented path.

---

## Verse Corpus Schema

`skills/sanskrit-wisdom/data/verses.json` — array of verse objects:

```jsonc
{
  "id":              "bg-9.22",               // unique key
  "devanagari":      "अनन्याश्चिन्तयन्तो...", // Sanskrit in Devanagari
  "transliteration": "ananyāś cintayanto...", // IAST transliteration
  "meaning":         "To those who worship...",
  "source":          "Bhagavad Gita 9.22",
  "deity":           "Krishna",
  "sampradaya":      "Vedanta/Gita",           // tradition
  "category":        "Bhakti Yoga",            // verse type
  "tags":            ["devotion","vishnu",...], // keyword search tags
  "use_cases":       ["protection","devotion"], // practice contexts
  "observance_tags": ["ekadashi","purnima"],    // tithis this verse suits
  "birth_tags":      ["vishnu","punarvasu"]     // birth-profile alignment
}
```

The four tag arrays are unioned into one set for scoring. `observance_tags` and `birth_tags` are the scoring-critical fields added as part of the weekly guidance build.

---

## Key Design Decisions

### Deterministic scoring over LLM ranking
Verse selection uses weighted tag matching, not a language model. The output is traceable — you can read the score formula and understand exactly why a verse was chosen. LLM ranking would produce unstable results on a 15-verse corpus and make the memory/rotation system harder to reason about.

### Local Practice Timing
The system uses Telugu / Smarta Vedic rules, then computes the actual practice day and timing for the configured local place. This keeps recommendations culturally grounded while making sunrise, sunset, Rahu Kalam, Pradosham, and fasting guidance actionable in New Jersey.

### Flat code structure (Karpathy-inspired)
Functions stay under 30 lines. No service layer, no repository pattern, no factory classes. The full logic chain from config load to output is readable in one pass. List comprehensions over loops, type hints on signatures only.

### Memory as a JSON file, not a database
The history is written to a simple JSON file (`shloka_history.json`) that lives in `dashboard/data/` and is committed to the repo. This makes the memory visible, diffable in git, and requires no infrastructure. Current-week live runs update it by default; backtests require `--write-history`.

### Graceful degradation for optional services
Both MLflow and Qdrant use availability checks on first access. If either is absent, the respective module silently no-ops. The core CLI — birth chart + panchangam + verse scoring — works with `requirements-core.txt`; dashboard, MLflow, and RAG dependencies are split into optional requirement files.

---

## Optional Integrations

| Integration | File | Activation |
|-------------|------|------------|
| MLflow tracking | `skills/ml-experiment/tracker.py` | Set `MLFLOW_TRACKING_URI` env var; `features.mlflow_tracking: true` in config |
| Qdrant semantic search | `skills/sanskrit-wisdom/scripts/verse_search.py` | Run `ingest.py` to build local store; `features.qdrant_rag: true` in config |
| Slack notifications | `scripts/slack_notify.py` | Set `SLACK_WEBHOOK_URL` secret in GitHub or env |
| Supermemory sync | `scripts/supermemory_sync.py` | Set `SUPERMEMORY_API_KEY`; `features.supermemory_sync: true` in config |

---

## Dependency Graph

```
weekly_guidance.py
  ├── panchang.py
  │     └── swisseph (C lib via pyswisseph)
  ├── janam_patri.py
  │     └── swisseph
  ├── verses.json
  ├── config.yaml  (via yaml)
  └── shloka_history.json

weekly_notification.py
  ├── panchang.py
  ├── janam_patri.py
  ├── verse_search.py
  │     ├── verses.json
  │     ├── [qdrant-client]  (optional)
  │     └── [sentence-transformers]  (optional)
  └── tracker.py
        └── [mlflow]  (optional)

slack_notify.py
  ├── weekly_guidance.py
  └── httpx

export_mlflow_runs.py / export_to_sqlite.py
  └── [mlflow] → dashboard/data/
```
