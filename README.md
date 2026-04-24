# Vedic Wisdom Weekly

A configurable weekly Sanskrit guidance system for Hindu practice, with local panchangam timing, Sanskrit verse recommendations, Slack delivery, and a static dashboard.

Given a birth profile and the upcoming 7-day local panchangam, it answers:

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

**Day Quality** — scored 1–5 for the configured birth profile, with a plain-English reason

**Color & Vastu** — Jyotish-keyed color to wear, color to avoid, gemstone, and which direction/corner of your home to activate

**Devata Shloka** — the deity of the tithi (Vishnu on Ekadashi, Shiva on Pradosham, Ganesha on Chaturthi, etc.) with full Devanagari + transliteration + meaning

**Personal Shloka** — scored against your birth profile, never repeats within the week, evolves across weeks via memory

**Practice Guidance** — specific instructions: fast rules for Ekadashi, twilight puja timing for Pradosham, tarpana guidance for Amavasya; weekday-specific mantra practice otherwise

### Sample header

```
══════════════════════════════════════════════════════════════
  VEDIC WEEKLY GUIDANCE
  Week of Apr 23 – Apr 29, 2026
  Practice Location: Local City (America/New_York)
  Janma Nakshatra: configured  |  Rashi: configured
  Tradition: Smarta
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

Copy `config.example.yaml` to private `config.yaml` for local use:

```bash
cp config.example.yaml config.yaml
```

For GitHub Actions, put the full private YAML content in the repository secret `VEDIC_CONFIG_YAML`. The tracked example config is intentionally generic.

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
config.example.yaml                      # Public template; private config.yaml is gitignored
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
    .gitkeep                             # Generated dashboard data is private / untracked
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
4. Generates dashboard data for the workflow artifact without committing private data
5. Optionally deploys dashboard to GitHub Pages

Required secrets: `SLACK_WEBHOOK_URL`, `SLACK_MEMBER_ID`, and `VEDIC_CONFIG_YAML`. `DASHBOARD_URL` is optional and should only be set after the dashboard is deployed somewhere. `MLFLOW_TRACKING_URI` is optional for historical run export.

GitHub Pages deploy is gated by the repository variable `ENABLE_GITHUB_PAGES=true`. Private repositories may require a paid GitHub plan for Pages; leave the variable unset to keep the weekly Slack/data workflow green.

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

MIT or private use, depending on your repository policy.
