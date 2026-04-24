# Vedic Wisdom Weekly

A personal weekly Sanskrit guidance system for **Saketh** — Golconda Vyapari Niyogi Brahmin, Smarta tradition (Apastamba Dharmasutra).

Given a birth profile (Punarvasu nakshatra, Mithuna rashi) and the upcoming 7-day local panchangam, it answers:

> *How does this week affect me personally? Which shlokas should I chant each day, what should I do, what should I avoid, and what are the best timings?*

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the technical deep-dive.

---

## Quick Start

```bash
pip install -r requirements.txt

# Full 7-day personalized guidance (primary command)
python scripts/weekly_guidance.py

# Backtest any week
python scripts/weekly_guidance.py --start-date 2026-05-04

# Birth chart verse recommendations
python scripts/janam_patri.py

# Search verses directly
python skills/sanskrit-wisdom/scripts/verse_search.py "karma yoga"
```

---

## What You Get

Running `weekly_guidance.py` prints a 7-day report. For each day:

**Panchangam** (local practice location, with Telugu / Smarta rules)
- Tithi · Nakshatra · Yoga · Karana · Vaara

**Muhurta Timings (local time)**
- Sunrise / Sunset
- Rahu Kalam — avoid starting new things
- Yamagandam — avoid travel and decisions
- Gulika Kalam — proceed with awareness
- Abhijit Muhurta — most auspicious window (~solar noon)

**Day Quality** — scored 1–5 for your Punarvasu + Mithuna birth profile, with a plain-English reason

**Color & Vastu** — Jyotish-keyed color to wear, color to avoid, gemstone, and which direction/corner of your home to activate

**Devata Shloka** — the deity of the tithi (Vishnu on Ekadashi, Shiva on Pradosham, Ganesha on Chaturthi, etc.) with full Devanagari + transliteration + meaning

**Personal Shloka** — scored against your birth profile, never repeats within the week, evolves across weeks via memory

**Practice Guidance** — specific instructions: fast rules for Ekadashi, twilight puja timing for Pradosham, tarpana guidance for Amavasya; weekday-specific mantra practice otherwise

### Sample header

```
══════════════════════════════════════════════════════════════
  VEDIC WEEKLY GUIDANCE — Saketh
  Week of Apr 23 – Apr 29, 2026
  Practice Location: New Jersey (America/New_York)
  Janma Nakshatra: Punarvasu  |  Rashi: Mithuna
  Tradition: Golconda Vyapari Niyogi Brahmin (Smarta)
══════════════════════════════════════════════════════════════

WEEK OVERVIEW
────────────────────────────────────────
Observances:
  ✦ Ekadashi — Apr 27
  ✦ Pradosham — Apr 29
Best days:      Thursday Apr 23, Monday Apr 27, Wednesday Apr 29
Caution days:   Tuesday Apr 28
```

---

## Configuration

Edit `config.yaml` to set your birth details and preferences:

```yaml
janam_patri:
  enabled: true
  birth_date: "2000-04-11"
  birth_time: "10:30"
  birth_place:
    lat: 28.6139        # New Delhi
    lon: 77.2090
    tz_offset: 5.5      # IST
  rashi: Mithuna        # set if known, else computed
  janma_nakshatra: Punarvasu

practice_location:
  city: New Jersey
  lat: 40.7128
  lon: -74.2060
  timezone: America/New_York

observances:
  - { name: Ekadashi,  deity: Vishnu,  priority: high }
  - { name: Pradosham, deity: Shiva,   priority: high }
  - { name: Amavasya,  deity: Pitrus,  priority: high }
  - { name: Purnima,   deity: All,     priority: medium }
  - { name: Sankashti Chaturthi, deity: Ganesha, priority: medium }
```

---

## All Commands

| Command | What it does |
|---------|-------------|
| `python scripts/weekly_guidance.py` | **Primary** — 7-day personalized guidance; writes shloka memory |
| `python scripts/weekly_guidance.py --start-date YYYY-MM-DD --no-write-history` | Backtest any week without mutating memory |
| `python scripts/weekly_notification.py` | Legacy weekly digest path |
| `python scripts/janam_patri.py` | Birth chart + nakshatra verse recommendations |
| `python scripts/slack_notify.py` | Post weekly digest to Slack webhook |
| `python scripts/export_mlflow_runs.py` | Export MLflow data → dashboard JSON |
| `python scripts/export_to_sqlite.py` | Export → SQLite (for Streamlit / BI tools) |
| `python scripts/serve_dashboard.py` | Serve static dashboard at localhost:8080 |
| `python skills/sanskrit-wisdom/scripts/verse_search.py "query"` | Search verse corpus |
| `python skills/karpathy-code-quality/guardrails.py .` | Lint project |
| `mlflow ui --port 5000` | Browse experiment tracking |

---

## Project Structure

```
config.yaml                              # Birth profile, observances, feature flags
scripts/
  weekly_guidance.py                     # ★ Primary: 7-day guidance (local timings + memory)
  panchang.py                            # Swiss Ephemeris panchangam engine
  janam_patri.py                         # Birth chart + nakshatra verse recs
  weekly_notification.py                 # Legacy digest wrapper / older MLflow path
  slack_notify.py                        # Slack webhook post
  serve_dashboard.py                     # Local static server (port 8080)
  export_mlflow_runs.py                  # Export MLflow → dashboard/data/*.json
  export_to_sqlite.py                    # Export → dashboard/data/vedic_wisdom.db
  supermemory_sync.py                    # Sync to Supermemory API (optional)
dashboard/
  index.html                             # Static dashboard (GitHub Pages)
  data/
    shloka_history.json                  # Memory: shlokas used per week (auto-updated)
    recommendations.json                 # Exported weekly recommendation history
    janam_patri.json                     # Exported birth chart + verse data
    vedic_wisdom.db                      # SQLite export (Streamlit / BI)
skills/
  sanskrit-wisdom/
    data/verses.json                     # Curated verse corpus (15 verses, fully tagged)
    scripts/verse_search.py              # Keyword + Qdrant semantic search
    scripts/ingest.py                    # Ingest Gita into Qdrant vector store
  ml-experiment/
    tracker.py                           # MLflow tracking (gracefully skipped if absent)
  karpathy-code-quality/
    guardrails.py                        # AST linter (nested try, func length, etc.)
docs/
  PLAN.md                                # Early planning notes (historical)
.github/workflows/
  weekly-digest.yml                      # Sunday CI: digest → Slack → dashboard → Pages
```

---

## Automation (GitHub Actions)

Every Sunday at 8 AM Eastern the CI pipeline runs automatically:

1. Generates weekly guidance (`weekly_guidance.py --write-history`)
2. Posts to Slack (`slack_notify.py`)
3. Exports dashboard data (`export_mlflow_runs.py`, `export_to_sqlite.py`)
4. Commits updated `dashboard/data/` back to `main`
5. Deploys dashboard to GitHub Pages

Required secrets: `SLACK_WEBHOOK_URL`, `SLACK_MEMBER_ID`. The Slack dashboard link is inferred in GitHub Actions from the repo name; `DASHBOARD_URL` is only needed if you want to override it. `MLFLOW_TRACKING_URI` is optional for historical run export.

---

## Verse Corpus

15 curated verses in `skills/sanskrit-wisdom/data/verses.json` covering all five Panchayatana deities:

| Deity | Verses |
|-------|--------|
| Vishnu / Krishna | BG 2.47, 4.7, 9.22, 6.5, 18.66 · Vishnu Sahasranama 1 |
| Shiva | Panchakshari Stotram · Mahamrityunjaya (Rig Veda 7.59.12) |
| Devi | Durga Saptashati 5.15 |
| Ganesha | Vakratunda Shloka |
| Surya | Gayatri Mantra (Rig Veda 3.62.10) · Aditya Hridayam 9 |
| Saraswati | Saraswati Vandana |
| Pitrus | Pitru Stotram |

Each verse carries `use_cases`, `observance_tags`, and `birth_tags` for deterministic scoring. See ARCHITECTURE.md for the scoring algorithm.

---

## Stack

| Library | Purpose |
|---------|---------|
| `pyswisseph` | Swiss Ephemeris — tithi, nakshatra, sunrise/sunset |
| `pyyaml` | Config loading |
| `mlflow` | Experiment tracking (optional) |
| `qdrant-client` | Vector search over larger corpora (optional) |
| `sentence-transformers` | Verse embeddings for Qdrant (optional) |
| `httpx` | HTTP client (Slack, Supermemory) |
| `streamlit` | Dashboard UI (optional) |
| `pandas` | Data export and analysis |

Install only the core CLI dependencies with `pip install -r requirements-core.txt`. The top-level `requirements.txt` installs core plus dashboard, MLflow, and RAG extras.

---

## License

Private / personal use.
