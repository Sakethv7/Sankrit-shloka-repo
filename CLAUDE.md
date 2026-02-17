# CLAUDE.md

## Project: Vedic Wisdom Weekly
Weekly Hindu practice notifications for Golconda Vyapari Niyogi Brahmin (Smarta tradition). Integrates Telugu Panchangam, Sanskrit verse RAG, MLflow tracking, and Supermemory.

## Owner
**Saketh** | Data Scientist @ J&J

## Stack
Python 3.11+ | httpx | MLflow | Qdrant (optional) | Supermemory (optional)

## Commands
```bash
python scripts/weekly_notification.py                              # Tithi-aware weekly digest (EST) + shlokas
python scripts/janam_patri.py                                      # Birth chart shloka recommendations
python scripts/export_mlflow_runs.py                               # Export data for dashboard
python scripts/serve_dashboard.py                                  # Serve dashboard at http://localhost:8080
python skills/sanskrit-wisdom/scripts/verse_search.py "karma yoga" # Search verses
python skills/karpathy-code-quality/guardrails.py .                # Lint project
mlflow ui --port 5000                                              # Tracking UI
```

## Code Rules (STRICT - Karpathy-inspired)
```python
# NEVER: Nested try/catch, verbose loops, factory patterns, over-abstraction
# ALWAYS: One-liners, comprehensions, flat booleans, helper functions

# BAD                              # GOOD
result = []                        result = [x.name for x in items if x.active]
for x in items:
    if x.active:
        result.append(x.name)

# BAD                              # GOOD
if user:                           return user and (user.admin or resource.public)
    if user.admin:
        return True
    else:
        if resource.public:
            return True
return False
```

**More rules:**
- Functions < 30 lines
- Extract helper if code repeats 3x
- `httpx` > `requests`
- `dataclasses` > Pydantic (unless validation needed)
- Type hints on signatures, not intermediate vars

## Structure
```
scripts/
  weekly_notification.py          # Tithi-aware digest (panchangam + verse per day)
  janam_patri.py                  # Birth nakshatra/rashi + shloka recommendations
  export_mlflow_runs.py           # Export MLflow + janam patri to dashboard data
  serve_dashboard.py              # Local server for dashboard
  supermemory_sync.py             # Long-term memory push to Supermemory API
dashboard/
  index.html                      # Dashboard UI (janam patri, insights, history)
  data/                           # recommendations.json, janam_patri.json (generated)
  README.md                       # How to run the dashboard
skills/
  sanskrit-wisdom/
    scripts/verse_search.py       # Keyword search over verse corpus (Qdrant-ready)
    data/verses.json              # 10 curated verses (Gita, Vishnu Sahasranama, Shiva, Ganesha, Gayatri, Pitru)
  ml-experiment/
    tracker.py                    # MLflow tracking for searches & notifications
  karpathy-code-quality/
    guardrails.py                 # AST-based linter (nested try, func length, loop->comprehension)
config.yaml                       # User preferences & tradition settings
```

## Domain Knowledge

### Golconda Vyapari Niyogi Brahmin
- **Tradition**: Smarta (Advaita Vedanta, non-sectarian)
- **Worship**: Panchayatana (Shiva, Vishnu, Devi, Ganesha, Surya)
- **Sutras**: Apastamba Dharmasutra
- **Observances**: Ekadashi (Vishnu), Pradosham (Shiva), Amavasya (ancestors)
- **Primary Mantra**: Om Namo Bhagavate Vasudevaya

### Telugu Calendar
- System: Amanta | Era: Salivahana Saka | New Year: Ugadi

## TODOs
- [ ] Optional: DrikPanchang API integration (current panchang uses Swiss Ephemeris)
- [ ] Optional: Qdrant embeddings for full Gita (ingest exists; ensure it runs in CI cache)
- [ ] Supermemory MCP for Claude Desktop
- [ ] Email/push notifications
- [x] Dashboard (static HTML; see dashboard/README.md) + GitHub Pages deploy

## Env Vars
```bash
SUPERMEMORY_API_KEY=sm_...        # Optional — for memory sync
MLFLOW_TRACKING_URI=sqlite:///mlflow.db
```

## Sanskrit Output Format
Prefer all three when context allows: **Devanagari** + **Transliteration** + **Meaning**
