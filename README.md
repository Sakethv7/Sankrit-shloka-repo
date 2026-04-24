# Vedic Wisdom Weekly

A personal weekly Sanskrit guidance system for **Saketh** — Golconda Vyapari Niyogi Brahmin, Smarta tradition.

Given a birth profile (Punarvasu nakshatra, Mithuna rashi) and the upcoming 7-day Telugu panchangam window, it answers one practical question:

> *How does this week affect me, which shlokas should I use as anchors, what should I do on each day, and what should I avoid?*

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# This week's full 7-day personalized guidance (primary command)
python scripts/weekly_guidance.py

# Backtest any week
python scripts/weekly_guidance.py --start-date 2026-05-04

# Legacy: weekly digest (EST, Slack-style)
python scripts/weekly_notification.py

# Birth chart verse recommendations
python scripts/janam_patri.py
```

---

## What `weekly_guidance.py` Produces

One run outputs a 7-day report. For each day:

### Panchangam (IST, New Delhi reference)
- **Tithi** (lunar day) — e.g. Shukla Ekadashi
- **Nakshatra** (Moon's constellation)
- **Yoga** (Sun+Moon combined quality — auspicious/inauspicious)
- **Karana** (half-tithi)
- **Vaara** (weekday in Sanskrit + English)

The panchangam is computed against **New Delhi coordinates in IST** — the standard reference for Telugu Vedic calendars. This gives the same tithi/nakshatra values you'd see in a printed Panchangam from Andhra Pradesh.

### Muhurta Timings (IST)
| Timing | What it means |
|--------|---------------|
| **Sunrise / Sunset** | Day boundaries for the Indian calendar day |
| **Rahu Kalam** | Inauspicious window — avoid starting important things |
| **Yamagandam** | Inauspicious window — avoid travel and major decisions |
| **Gulika Kalam** | Mildly inauspicious — proceed with awareness |
| **Abhijit Muhurta** | Most auspicious window of the day (~solar noon ±30 min) |

Rahu Kalam and Yamagandam are computed from actual sunrise/sunset (Swiss Ephemeris), not fixed clock times.

### Day Quality for Saketh
Each day is scored 1–5 based on:
- **Weekday planet**: Thursday (Jupiter/Guru) = 5, Wednesday (Mercury/Budha) = 4, Monday (Moon) = 4, Saturday/Tuesday = 2
- **Nakshatra compatibility**: Punarvasu is highly compatible with Pushya, Ashlesha, Vishakha, Swati
- **Observance bonus**: Ekadashi, Pradosham, Amavasya, Purnima, Chaturthi each add +1

The quality message explains *why* — not just a number.

### Color & Vastu
Every day has a Jyotish-keyed color recommendation:
- **Wear**: the planet's favored color (yellow/gold on Thursday, green on Wednesday, white on Monday, etc.)
- **Avoid**: the conflicting color
- **Gemstone** associated with the day's planet
- **Vastu direction**: which corner/wall of the home to activate that day

### Devata Shloka of the Day
Selected by **tithi deity** — the deity associated with the lunar day:
- Ekadashi / Dwadashi / Purnima → Vishnu
- Pradosham / Chaturdashi / Saptami → Shiva
- Chaturthi (Sankashti) → Ganesha
- Ashtami / Navami → Durga
- Amavasya → Pitrus (ancestors)
- Panchami / Saptami → Surya
- etc.

Shown in full: **Devanagari + transliteration + meaning**.

### Personal Shloka of the Day
Selected by birth profile + week context + memory:
- Scored against `["punarvasu", "mithuna", "smarta", "vishnu"]` birth tags
- Boosted by the day's observance if present
- **Never repeats within the same 7-day cycle** (hard exclusion)
- **Penalized if used recently** (soft penalty across prior weeks)

### Practice Guidance
On observance days: specific instruction (fast rules for Ekadashi, twilight puja timing for Pradosham, tarpana guidance for Amavasya, etc.).

On regular days: vaara-specific practice (e.g. recite Gayatri 108× at sunrise on Sunday, Saraswati Vandana on Wednesday, Hanuman Chalisa on Saturday).

---

## Design Decisions

### Why IST and New Delhi for the calendar?
The Telugu Panchangam is traditionally published for Indian Standard Time with calculations anchored to the Indian subcontinent. Tithis and nakshatras cross midnight at different times depending on longitude — using IST keeps the calendar consistent with what a printed Panchangam from Andhra Pradesh would show. Muhurta timings (Rahu Kalam etc.) are also given in IST for the same reason.

### Why deterministic scoring instead of LLM ranking?
The verse selection uses a weighted rule system:
```
+3 per observance-tag match
+2 per birth-tag match
+1 Smarta sampradaya bonus
-2 generic-verse penalty (tagged "daily" with no other match)
-4 recently-used penalty (history)
hard exclude: same-week personal shlokas
```

This makes the output **traceable** — you can always understand why a verse was chosen. Semantic search (Qdrant embeddings) is optional and not required for core output.

### Memory evolution
`dashboard/data/shloka_history.json` stores which shlokas were used each week. The scoring system:
- **Hard-excludes** personal shlokas already used this week (7 unique personal shlokas per run)
- **Penalizes** shlokas used in prior weeks (they can return after a few weeks)
- This means the system naturally rotates through the corpus and evolves over time

### Why Punarvasu + Mithuna scoring?
Punarvasu is ruled by Jupiter (Guru) and has themes of renewal, home, and abundance (Aditi). Mithuna (Gemini) is ruled by Mercury (Budha). This makes:
- **Thursday (Jupiter)** and **Wednesday (Mercury)** the best days
- **Mars (Tuesday)** and **Saturn (Saturday)** the most challenging
- Nakshatra days of Pushya and Ashlesha (adjacent to Punarvasu in the sky) highly compatible

---

## Verse Corpus

Located at `skills/sanskrit-wisdom/data/verses.json`. Each verse has:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (e.g. `bg-2.47`, `shiva-panchakshari`) |
| `devanagari` | Sanskrit in Devanagari script |
| `transliteration` | IAST transliteration |
| `meaning` | English meaning |
| `source` | Text reference (e.g. "Bhagavad Gita 2.47") |
| `deity` | Primary deity |
| `sampradaya` | Tradition (Smarta, Vaishnava, Shaiva, etc.) |
| `category` | Type (Mantra, Stotra, Karma Yoga, etc.) |
| `tags` | Keyword tags for search |
| `use_cases` | Practice contexts (focus, protection, ancestral, etc.) |
| `observance_tags` | Tithis this verse is ideal for (ekadashi, pradosham, etc.) |
| `birth_tags` | Birth-profile alignment (punarvasu, mithuna, smarta, etc.) |

Current corpus (15 verses):
- **Bhagavad Gita**: 2.14, 2.47, 4.7, 6.5, 9.22, 18.66
- **Vishnu Sahasranama**: verse 1
- **Shiva**: Panchakshari Stotram, Mahamrityunjaya (Rig Veda 7.59.12)
- **Ganesha**: Vakratunda shloka
- **Devi**: Durga Saptashati 5.15 (Ya Devi Sarva Bhutesu)
- **Surya**: Gayatri Mantra (Rig Veda 3.62.10), Aditya Hridayam v.9
- **Saraswati**: Saraswati Vandana
- **Pitrus**: Pitru Stotram

---

## Tradition Context

**Golconda Vyapari Niyogi Brahmin** — Smarta tradition, Apastamba Dharmasutra.

Smarta Brahmins follow **Panchayatana puja**: simultaneous worship of five deities as aspects of one Brahman — Shiva, Vishnu, Devi, Ganesha, and Surya. This is why the verse corpus intentionally covers all five (not just Vishnu or Shiva), and why the scoring favors Smarta sampradaya verses.

Primary mantra: **Om Namo Bhagavate Vasudevaya**

Key observances tracked:
| Observance | Deity | Priority |
|-----------|-------|----------|
| Ekadashi | Vishnu | High |
| Pradosham | Shiva | High |
| Amavasya | Pitrus (ancestors) | High |
| Purnima | All | Medium |
| Sankashti Chaturthi | Ganesha | Medium |

---

## Other Scripts

| Script | Purpose |
|--------|---------|
| `scripts/panchang.py` | Swiss Ephemeris panchangam engine (tithi, nakshatra, yoga, karana, sunrise) |
| `scripts/janam_patri.py` | Birth chart computation + verse recommendations by nakshatra theme |
| `scripts/weekly_notification.py` | Legacy: 7-day digest in EST (Slack-compatible format) |
| `scripts/slack_notify.py` | Post weekly digest to Slack webhook |
| `scripts/serve_dashboard.py` | Serve static dashboard at localhost:8080 |
| `scripts/export_mlflow_runs.py` | Export MLflow tracking data to dashboard JSON |
| `scripts/export_to_sqlite.py` | Export to SQLite for Streamlit / BI tool |
| `scripts/supermemory_sync.py` | Sync recommendations to Supermemory API (optional) |

---

## Project Structure

```
config.yaml                          # Birth profile, observances, feature flags
scripts/
  weekly_guidance.py                 # ★ Primary: 7-day personalized guidance (IST)
  panchang.py                        # Panchangam engine (Swiss Ephemeris)
  janam_patri.py                     # Birth chart + nakshatra verse recs
  weekly_notification.py             # Legacy weekly digest (EST)
  slack_notify.py                    # Slack webhook post
  serve_dashboard.py                 # Local dashboard server (port 8080)
  export_mlflow_runs.py              # Export MLflow → dashboard JSON
  export_to_sqlite.py                # Export → SQLite
  supermemory_sync.py                # Sync to Supermemory API
dashboard/
  index.html                         # Static dashboard UI
  data/
    shloka_history.json              # Memory: shlokas used per week (auto-updated)
    recommendations.json             # Exported recommendation history
    janam_patri.json                 # Exported birth chart data
skills/
  sanskrit-wisdom/
    data/verses.json                 # Verse corpus (15 curated verses)
    scripts/verse_search.py          # Keyword/tag search over corpus
  ml-experiment/
    tracker.py                       # MLflow tracking (graceful if unavailable)
  karpathy-code-quality/
    guardrails.py                    # AST linter (nested try, func length, etc.)
docs/
  PLAN.md                            # Early planning notes
```

---

## Stack

- **Python 3.11+**
- **pyswisseph** — Swiss Ephemeris for astronomical calculations (tithi, nakshatra, sunrise/set)
- **PyYAML** — config loading
- **MLflow** — experiment tracking (optional; gracefully skipped if unavailable)
- **Qdrant** — vector search for larger verse corpus (optional)
- **httpx** — HTTP client (Slack, Supermemory)

---

## Configuration (`config.yaml`)

```yaml
janam_patri:
  enabled: true
  birth_date: "2000-04-11"       # Your birth date
  birth_time: "10:30"            # Local birth time
  birth_place:
    lat: 28.6139                 # New Delhi
    lon: 77.2090
    tz_offset: 5.5               # IST
  rashi: Mithuna                 # Override if known
  janma_nakshatra: Punarvasu     # Override if known

calendar:
  timezone: America/New_York
  location: New Jersey

observances:                     # Tithis to track
  - name: Ekadashi
    deity: Vishnu
    priority: high
  # ... etc
```

---

## License

Private / personal use.
