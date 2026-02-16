# Vedic Wisdom Weekly — What You Wanted & What We Can Do

## What You Wanted

1. **Shlokas (Sanskrit) according to tithis of that week**  
   - Hindu calendar (Amanta, Salivahana Saka)  
   - In **EST** (you’re in New Jersey)

2. **Shlokas and recommendations according to your janam patri (birth chart)**  
   - Hindu way: birth nakshatra, rashi, deity associations, etc.

3. **A dashboard**  
   - See what you’ve been recommended  
   - Insights over time (e.g. which deities/verses, observance history)

---

## What’s Already There

| Feature | Status |
|--------|--------|
| **Panchang in EST** | ✅ `panchang.py` uses New Jersey lat/lon and `tz = -5` (EST). Sunrise and tithi are for local day. |
| **Weekly digest by observances** | ✅ `weekly_notification.py` gets the week’s tithis, detects Ekadashi, Pradosham, Amavasya, Purnima, Sankashti Chaturthi, and pairs **one** “verse of the week” via semantic/keyword search. |
| **Verse corpus** | ✅ Gita (700+) + stotras (Vishnu Sahasranama, Shiva, Ganesha, Gayatri, Pitru). Search by meaning/tags. |
| **MLflow logging** | ✅ Each run logs week, observance_count, verse_id, digest_text — good for a dashboard. |
| **Janam patri** | ❌ Not implemented. No birth time/place or rashi/nakshatra-based recommendations. |
| **Explicit “shloka per tithi” for the week** | ⚠️ Partial. You get one verse for the week based on observances; there’s no per-day tithi → shloka list. |
| **Dashboard** | ❌ In TODOs; no UI yet. |

So: **tithi-based logic** is there (observances are tithi-based in EST), but the product is “one verse for the week” rather than “one shloka per tithi.” **Janam patri** and **dashboard** are the main gaps.

---

## What We Can Do

### 1. Tithi-based shlokas for the week (EST)

- **Keep** panchang and EST as-is (already correct for New Jersey).
- **Add** a “tithi of the day” view for the week: for each of the 7 days show **Paksha + Tithi**, and either:
  - **Option A:** One “verse of the week” (current) plus a short line per day: “Today’s tithi: Krishna Ekadashi — consider Vishnu / Ekadashi verses.”
  - **Option B:** Recommend **one shloka per day** (or per unique tithi in the week) using a small **tithi → deity/theme** map (e.g. Ekadashi → Vishnu, Chaturthi → Ganesha, Amavasya → Pitru) and existing verse search.
- **Output:** Same weekly digest, but explicitly keyed by date and tithi, so you can practice “today’s” shloka the Hindu way.

### 2. Janam patri–based recommendations (Hindu way)

- **Config:** Add a `janam_patri` section in `config.yaml`: birth date, time, place (lat/lon or city), timezone.
- **Compute:** Use Swiss Ephemeris (already in use for panchang) to get:
  - **Birth nakshatra** (janma nakshatra)  
  - **Birth rashi** (moon sign)  
  - Optionally: weekday (vaara), lagna later.
- **Recommendations:**
  - Map **janma nakshatra** → deity (e.g. nakshatra lords: Ashwini → Ketu, Bharani → Venus, …) and/or use traditional “nakshatra deity” lists.
  - Recommend **shlokas/mantras** by that deity and by “birth nakshatra” tags if we add them to verses.
- **Output:** A small script or API: “Given my janam patri, recommend these verses/mantras for my nakshatra/rashi.”

### 3. Dashboard (recommendations + insights)

- **Data source:** MLflow (SQLite) already has: week, observance_count, verse_id, verse_source, observances, search_query, digest_text.
- **Features:**
  - **History:** List of weekly digests (date range, verse of the week, observances).
  - **Insights:** Most recommended verses, most frequent observances, deity/source distribution.
- **Tech:** React app (as in TODOs) that either:
  - Reads MLflow SQLite via a thin Python/Flask API, or  
  - Uses an exported JSON/CSV of runs (e.g. from a small export script) so the front end stays static.
- **Optional:** Later add janam-patri-based recommendations and tithi-of-the-day to the same dashboard.

---

## Suggested Order

1. **Tithi-aware weekly digest** — Extend `weekly_notification.py` so the digest clearly lists each day’s tithi (EST) and either one verse per tithi/day or one verse of the week + tithi hints.  
2. **Janam patri** — Add `janam_patri` to config, add `scripts/janam_patri.py` (or under `skills/`) to compute nakshatra/rashi and return recommended verses.  
3. **Dashboard** — Export MLflow runs to JSON; build a simple React (or single-page) dashboard to show past recommendations and basic insights.

---

## Files to Touch (summary)

| Goal | Files |
|------|--------|
| Tithi-based shlokas | `scripts/weekly_notification.py`, optionally `scripts/panchang.py` (no change if we only use existing `compute()`) |
| Janam patri | `config.yaml` (new section), new `scripts/janam_patri.py`, optionally tag verses with nakshatra in `verses.json` / ingest |
| Dashboard | New `dashboard/` (React or HTML+JS), optional `scripts/export_mlflow_runs.py` |

This keeps your stack (Python, httpx, MLflow, Qdrant, EST panchang) and adds the Hindu-calendar and janam-patri layers plus a single place to see recommendations and insights.
