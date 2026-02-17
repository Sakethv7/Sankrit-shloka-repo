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

## What’s Already There (Current State)

| Feature | Status |
|--------|--------|
| **Panchang in EST** | ✅ `panchang.py` uses New Jersey lat/lon and `tz = -5` (EST). Sunrise and tithi are for local day. |
| **Weekly digest by observances** | ✅ `weekly_notification.py` gets the week’s tithis, detects Ekadashi, Pradosham, Amavasya, Purnima, Sankashti Chaturthi, and pairs **one** “verse of the week” via semantic/keyword search. |
| **Verse corpus** | ✅ Gita (700+) + stotras (Vishnu Sahasranama, Shiva, Ganesha, Gayatri, Pitru). Search by meaning/tags. |
| **MLflow logging** | ✅ Each run logs week, observance_count, verse_id, digest_text — good for a dashboard. |
| **Janam patri** | ✅ Implemented with nakshatra/rashi + verse recs and lifestyle guidance. |
| **Explicit “shloka per tithi” for the week** | ✅ Implemented (daily verses are computed and exported). |
| **Dashboard** | ✅ Static HTML + GitHub Pages deploy with KPIs and trends. |

So: **tithi-based logic** is there and daily verses are computed. **Janam patri** and **dashboard** are implemented and exported.

---

## What We Can Do Next

### 1. Improve tithi-based shloka presentation (EST)

- **Keep** panchang and EST as-is (already correct for New Jersey).
- **Current:** One verse of the week plus computed daily verses in exports.
- **Next:** Improve the UI to surface daily verses more clearly or collapse by unique tithi for the week.

### 2. Janam patri–based recommendations (Hindu way)

- **Current:** Implemented with nakshatra/rashi, theme, and lifestyle guidance.
- **Next:** Add explicit sampradaya/deity metadata to verse corpus for better filtering.

### 3. Dashboard (recommendations + insights)

- **Data source:** MLflow (SQLite) and exported JSON. Dashboard reads JSON for GitHub Pages.
- **Features:**
  - **History:** List of weekly digests (date range, verse of the week, observances).
  - **Insights:** Most recommended verses, most frequent observances, deity/source distribution.
- **Tech:** Static HTML + JS (current). Optional future: React or a small API-backed UI.

---

## Suggested Order

1. **Metadata** — Add sampradaya/script/deity tags to verse corpus and exports.  
2. **Dashboard** — Surface these tags in KPIs and trend charts.  
3. **Recommendations** — Expand lifestyle recs and routine suggestions.

---

## Files to Touch (summary)

| Goal | Files |
|------|--------|
| Tithi-based shlokas | `scripts/weekly_notification.py`, optionally `scripts/panchang.py` (no change if we only use existing `compute()`) |
| Janam patri | `scripts/janam_patri.py`, `config.yaml`, optional tagging in `verses.json` |
| Dashboard | `dashboard/index.html`, `scripts/export_mlflow_runs.py` |

This keeps your stack (Python, httpx, MLflow, Qdrant, EST panchang) and adds the Hindu-calendar and janam-patri layers plus a single place to see recommendations and insights.
