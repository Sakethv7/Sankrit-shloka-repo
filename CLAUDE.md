# CLAUDE.md

## Project: Vedic Wisdom Weekly
Weekly Hindu practice notifications for Golconda Vyapari Niyogi Brahmin (Smarta tradition). Integrates Telugu Panchangam, Sanskrit verse RAG, MLflow tracking, and Supermemory.

## Owner
**Saketh** | Data Scientist @ J&J

## Stack
Python 3.11+ | httpx | MLflow | Qdrant (optional) | Supermemory (optional)

## Commands
```bash
python scripts/weekly_notification.py                              # Generate weekly digest
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
  weekly_notification.py          # Main generator (panchangam + verse pairing)
  supermemory_sync.py             # Long-term memory push to Supermemory API
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
- [ ] DrikPanchang API integration (replace stub in weekly_notification.py)
- [ ] Qdrant embeddings for full Gita (replace keyword search in verse_search.py)
- [ ] Supermemory MCP for Claude Desktop
- [ ] Email/push notifications
- [ ] React dashboard

## Env Vars
```bash
SUPERMEMORY_API_KEY=sm_...        # Optional — for memory sync
MLFLOW_TRACKING_URI=sqlite:///mlflow.db
```

## Sanskrit Output Format
Always include all three: **Devanagari** + **Transliteration** + **Meaning**
