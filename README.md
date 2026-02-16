# Vedic Wisdom Weekly

Weekly Hindu practice notifications: **tithi-based Sanskrit shlokas** (EST), **janam patri** recommendations, and a simple dashboard. Built for Golconda Vyapari Niyogi Brahmin (Smarta tradition).

## What it does

- **Weekly digest** — Panchangam for the week (New Jersey / EST), observances (Ekadashi, Pradosham, Amavasya, etc.), and **one shloka per day** by tithi.
- **Janam patri** — Birth nakshatra & rashi (from config or computed via Swiss Ephemeris) and recommended shlokas.
- **Dashboard** — View janam patri verses, weekly recommendation history, and insights (MLflow-backed).
- **Slack** — Optional weekly post to a channel with @mention (GitHub Actions).

## Quick start

```bash
# Install
pip install -r requirements.txt

# This week's tithi-based shlokas (EST)
python scripts/weekly_notification.py

# Your birth-chart shloka recommendations
python scripts/janam_patri.py
```

## Config

Edit **`config.yaml`** for:

- **Calendar** — Location (default New Jersey), timezone (America/New_York).
- **Janam patri** — Birth date, time, place (e.g. New Delhi, IST). Optional: set `rashi` and `janma_nakshatra` (e.g. Mithuna, Punarvasu) to use your known chart.

## Dashboard

**Option A — Static HTML:**  
`python scripts/export_mlflow_runs.py` then `python scripts/serve_dashboard.py` → http://localhost:8080

**Option B — Modern (Streamlit + SQLite):**  
`python scripts/export_to_sqlite.py` then `streamlit run dashboard/streamlit_app.py`  
Data goes into one SQLite DB (metadata/tables); you can also plug Metabase, Superset, or Evidence into that DB.

See **`dashboard/README.md`** for details.

## How you get panchang & janam patri

| What | Where you get it |
|------|------------------|
| **Panchang** (week’s tithi, nakshatra, sunrise, observances) | In the **Slack digest** (both workflows), or run `python scripts/weekly_notification.py` locally. |
| **Shlokas by tithi** (one verse per day) | Same as panchang — included in the weekly digest in Slack or local output. |
| **Janam patri** (birth nakshatra/rashi + recommended shlokas) | **Not** in Slack. Run `python scripts/janam_patri.py` locally, or open the **dashboard** (after `export_mlflow_runs.py`) and see the “Janam Patri” section. |

So: **Slack = panchang + weekly shlokas.** **Local / dashboard = janam patri.**

## GitHub Actions: the two workflows

Both post the **same** weekly digest to Slack (panchang + observances + shloka by tithi + verse of the week). The difference is when and how they run:

| Workflow | Schedule | What it does |
|----------|---------|----------------|
| **Weekly Vedic Digest** | Sundays **13:00 UTC** (8am EST) | Full pipeline: cache verse data, optionally ingest Gita/stotras, **generate** digest (panchang + shlokas), **then** send to Slack. Use this if you want the “main” weekly run with verse data ensured. |
| **Weekly Slack Digest** | Sundays **12:00 UTC** (7am EST) | Lightweight: **only** runs `slack_notify.py`, which generates the digest on the fly and sends to Slack. No cache/ingest. Runs 1 hour earlier. |

**Recommendation:** Use **one** of them to avoid two Slack messages on Sunday. Prefer **Weekly Vedic Digest** (8am EST) for the full pipeline; you can disable or delete **Weekly Slack Digest** if you don’t need the earlier run.

**Secrets** (Settings → Secrets and variables → Actions):

- `SLACK_WEBHOOK_URL` — Incoming webhook URL for your channel.
- `SLACK_MEMBER_ID` — Your Slack user ID (for @mention).

## Commands

| Command | Description |
|--------|-------------|
| `python scripts/weekly_notification.py` | Tithi-aware weekly digest + shlokas |
| `python scripts/janam_patri.py` | Janam patri recommendations |
| `python scripts/export_mlflow_runs.py` | Export data for dashboard |
| `python scripts/serve_dashboard.py` | Serve dashboard (port 8080) |
| `python skills/sanskrit-wisdom/scripts/verse_search.py "karma yoga"` | Search verses |

## Structure

```
config.yaml           # User prefs, calendar, janam patri
scripts/
  weekly_notification.py   # Weekly digest (panchang + verse per tithi)
  janam_patri.py          # Birth chart + verse recommendations
  export_mlflow_runs.py   # Export for dashboard
  serve_dashboard.py     # Local dashboard server
  slack_notify.py        # Slack webhook post
  panchang.py            # Swiss Ephemeris panchangam (EST)
dashboard/              # Static dashboard (see dashboard/README.md)
skills/sanskrit-wisdom/  # Verse corpus + search (Qdrant/keyword)
skills/ml-experiment/    # MLflow tracking
```

## Stack

Python 3.11+ · pyswisseph · httpx · MLflow · Qdrant (optional) · sentence-transformers (optional)

## License

Private / personal use.
