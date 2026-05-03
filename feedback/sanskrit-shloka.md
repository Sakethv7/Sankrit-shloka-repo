# Sanskrit Shloka MVP Engineering Spec

## Product definition

This product is a personal weekly Sanskrit guidance CLI for Saketh. It uses Saketh's birth profile plus the upcoming 7-day Telugu panchangam window to answer one practical question:

`How does this week affect me, and which 1-2 shlokas should I use as remedies or anchors?`

The value is not generic "daily inspiration." The value is personalized weekly guidance tied to:

- janma nakshatra / rashi from birth profile
- this week's tithi / nakshatra / observance pattern
- a small curated set of remedial shlokas already stored locally

Success criterion for the MVP:

- running one terminal command produces a useful weekly readout in under 3 seconds on local data
- output feels specific to Saketh, not generic to any Hindu user
- output includes exactly 1-2 recommended shlokas with a short why-this-week explanation

## What the MVP is

The MVP is a single-user, terminal-first Python CLI that:

- reads birth details from `config.yaml`
- computes janma nakshatra/rashi if needed
- computes the next 7 days of panchangam locally using Swiss Ephemeris
- scores the week against the birth profile and important observances
- prints one weekly summary plus 1-2 relevant remedial shlokas

Concrete output shape:

1. Week window
2. Birth profile summary
3. Weekly signal summary
4. Top 2 reasons this week matters
5. One primary shloka
6. Optional second shloka if score gap is small enough
7. One-line practice guidance for each shloka

The CLI should prefer all three Sanskrit output forms when available:

- Devanagari
- Transliteration
- Meaning

## What the MVP is not

The MVP is not:

- a web app
- a dashboard
- a mobile app
- a notification system
- a multi-user product
- a chat assistant
- a generalized astrology platform
- a recommendation API for external consumers
- a vector-search-first system
- an always-on memory system

Explicitly excluded from MVP implementation:

- auth
- Redis
- email, push, Slack, SMS, calendar delivery
- background jobs
- remote APIs, unless a CLI command cannot work without one
- Supermemory integration
- MLflow instrumentation as a dependency for core output
- Qdrant as a dependency for core output

If Qdrant or MLflow exist in the repo, the MVP must still work when both are absent.

## Required inputs

Minimum required config:

- `janam_patri.enabled: true`
- `janam_patri.birth_date`
- `janam_patri.birth_time`
- `janam_patri.birth_place.lat`
- `janam_patri.birth_place.lon`
- `janam_patri.birth_place.tz_offset`

Optional but preferred inputs:

- `janam_patri.janma_nakshatra`
- `janam_patri.rashi`
- `user.tradition`
- `user.community`
- `observances`

Runtime inputs:

- target start date, default = today in `America/New_York`
- optional CLI flag to override week start date for backtesting

Corpus inputs:

- local shloka corpus in `skills/sanskrit-wisdom/data/verses.json`

Required corpus fields per verse:

- `id`
- `devanagari`
- `transliteration`
- `meaning`
- `source`
- `tags`
- `deity`
- `category`

Recommended additional corpus fields for this MVP:

- `use_cases`: `["focus", "protection", "ancestral", "obstacle_removal", "equanimity"]`
- `observance_tags`: `["ekadashi", "pradosham", "amavasya", "purnima", "chaturthi"]`
- `birth_tags`: `["punarvasu", "mithuna", "vishnu", "smarta"]`

These fields can be added later, but the MVP scoring logic is much cleaner if they exist.

## Exact files and modules

Primary CLI entrypoint:

- `scripts/weekly_guidance.py`

Modules to reuse directly:

- `scripts/panchang.py`
  - use `compute()`
  - use observance helpers like `is_ekadashi()`, `is_pradosham()`, `is_amavasya()`, `is_purnima()`, `is_chaturthi()`
- `scripts/janam_patri.py`
  - use `compute_birth_chart()`
  - reuse `load_janam_config()`
  - reuse or simplify `NAKSHATRA_THEME`
- `skills/sanskrit-wisdom/scripts/verse_search.py`
  - use `load_verses()`
  - do not make semantic search mandatory

Config and data files:

- `config.yaml`
- `skills/sanskrit-wisdom/data/verses.json`

Modules to avoid depending on for MVP correctness:

- `dashboard/index.html`
- `dashboard/streamlit_app.py`
- `scripts/serve_dashboard.py`
- `scripts/slack_notify.py`
- `scripts/supermemory_sync.py`
- `skills/ml-experiment/tracker.py`

Implementation structure for `scripts/weekly_guidance.py`:

- `get_birth_profile(config_path) -> BirthChart`
- `get_week_context(start_date) -> list[DailyPanchang], list[Observance]`
- `score_week_against_birth_profile(chart, panchang_days, observances) -> WeekScore`
- `score_verse(verse, week_score, chart, observances) -> float`
- `pick_top_verses(verses, week_score, top_k=2) -> list[VerseMatch]`
- `format_weekly_guidance(...) -> str`
- `main()`

Keep functions short and flat. No service layer, no repository layer, no factory layer.

## Recommendation/scoring logic

The scoring must stay deterministic and inspectable. No fake intelligence. No LLM ranking.

### 1. Build a week context

For the next 7 days:

- compute each day's `tithi`, `paksha`, `nakshatra`, `vaara`
- detect observances using existing helper functions

Aggregate into:

- observance counts by type
- list of unique weekly nakshatras
- list of high-priority observances
- earliest major observance in the window

### 2. Build a birth relevance profile

From birth config or computed chart:

- `janma_nakshatra`
- `rashi`
- base deity/theme from `NAKSHATRA_THEME`

Derive a small set of profile tags:

- nakshatra tag, e.g. `punarvasu`
- rashi tag, e.g. `mithuna`
- deity/theme tags from nakshatra theme, e.g. `vishnu`, `wisdom`, `home`, `abundance`
- tradition tags, e.g. `smarta`

### 3. Score the week

Compute a weekly signal map with explicit weights. Example:

- `+5` if `Ekadashi` occurs this week
- `+5` if `Pradosham` occurs this week
- `+5` if `Amavasya` occurs this week
- `+3` if `Purnima` occurs this week
- `+3` if `Sankashti Chaturthi` occurs this week
- `+2` if an observance deity matches the birth-theme deity
- `+2` if a weekly nakshatra is the same as janma nakshatra
- `+1` if the week contains a vaara traditionally aligned with the top observance deity

This should produce:

- `primary_week_theme`
- `secondary_week_theme`
- `reasons: list[str]`

Theme derivation rule:

- if `Amavasya` present, theme includes `ancestral`, `quiet`, `grounding`
- if `Ekadashi` present, theme includes `discipline`, `vishnu`, `upavasa`, `clarity`
- if `Pradosham` present, theme includes `shiva`, `release`, `forgiveness`
- if `Chaturthi` present, theme includes `ganesha`, `obstacle_removal`
- else use birth-theme deity + janma nakshatra theme

### 4. Score verses

Each verse gets a weighted score:

- `+5` if verse tags match primary weekly observance theme
- `+4` if verse deity matches primary week deity
- `+3` if verse tags match birth-theme tags
- `+2` if verse sampradaya is compatible with Smarta usage
- `+2` if verse category is remedial/mantra/stotra instead of abstract philosophy
- `-3` if verse is too generic and matches only broad tags like `daily` or `devotion`

Tie-breakers:

- prefer observance-specific verses over generic Gita verses
- prefer shorter, chantable verses for remedy slots
- limit to max one highly generic Bhagavad Gita verse unless no better option exists

Selection rule:

- always return one primary verse
- return a second verse only if its score is at least 80% of the primary score and it adds a different reason

Explanation rule:

Each selected verse must include a one-line reason in plain English, for example:

- `Chosen because Ekadashi falls this week and this verse directly supports Vishnu-centered discipline and steadiness.`
- `Chosen because Amavasya is the strongest weekly signal and this mantra is explicitly appropriate for pitru remembrance.`

## CLI flow

Command:

```bash
python scripts/weekly_guidance.py
```

Optional backtest:

```bash
python scripts/weekly_guidance.py --start-date 2026-04-26
```

Exact CLI flow:

1. Load `config.yaml`
2. Validate required birth fields
3. Compute or confirm `janma_nakshatra` and `rashi`
4. Compute next 7 days of panchangam
5. Detect weekly observances
6. Build week-theme scores
7. Load verse corpus from local JSON
8. Score all verses deterministically
9. Select top 1-2 verses
10. Print final report to stdout
11. Exit non-zero only for invalid config or missing corpus

Suggested stdout shape:

```text
Vedic Weekly Guidance
Week: 2026-04-26 to 2026-05-02

Birth profile
- Janma nakshatra: Punarvasu
- Rashi: Mithuna
- Base theme: Vishnu / renewal / home

Why this week matters
- Ekadashi falls within this 7-day window
- Your birth theme aligns with Vishnu-centered steadiness

Weekly guidance
- Keep the week lighter, cleaner, and less reactive than usual.
- Use one disciplined anchor practice instead of adding many rituals.

Recommended shlokas
1. Vishnu Sahasranama 1
   [Devanagari]
   [Transliteration]
   [Meaning]
   Why: Best direct match for Ekadashi + Vishnu alignment.

2. Bhagavad Gita 9.22
   [Devanagari]
   [Transliteration]
   [Meaning]
   Why: Reinforces reliance and steadiness during a devotional week.
```

## Risks and fake-smart traps

### Risk 1: generic output pretending to be personalized

If the same 2 Gita verses appear every week, the product is not proving value. Personalization must be traceable to:

- birth profile
- actual weekly observances
- explicit scoring reasons

Mitigation:

- print why each verse was chosen
- keep weighted scoring visible in code
- optionally add `--debug` to print top scoring factors

### Risk 2: overclaiming astrology precision

This MVP is not a full jyotisha engine. It should not claim:

- life predictions
- event certainty
- house-based forecasting
- dasha-based advice

Mitigation:

- frame output as `weekly spiritual guidance` and `practice recommendation`
- use observance + birth-theme alignment, not predictive astrology language

### Risk 3: semantic search making results look smart but unstable

Qdrant embeddings can make ranking opaque and brittle for a tiny corpus.

Mitigation:

- make keyword/tag scoring the default
- allow semantic search only as optional fallback, not core ranking logic

### Risk 4: too much product before proof of value

Dashboard, notifications, memory sync, and APIs can consume time without proving the core question.

Mitigation:

- keep one CLI, one config, one local corpus, one report
- defer all delivery surfaces until the CLI is genuinely useful week after week

### Risk 5: bad corpus structure

If the verses lack observance-specific and remedy-specific tags, ranking will be fake-smart.

Mitigation:

- add explicit tags for use case and observance fit
- prefer a smaller, well-tagged corpus over a larger messy corpus

## Top 3 implementation steps

1. Build `scripts/weekly_guidance.py` as a pure local CLI that combines `config.yaml`, `scripts/panchang.py`, `scripts/janam_patri.py`, and local verse loading into one deterministic weekly report.

2. Tighten `skills/sanskrit-wisdom/data/verses.json` for MVP ranking by adding observance and remedy tags so the system can distinguish `Ekadashi`, `Pradosham`, `Amavasya`, `Chaturthi`, focus, protection, obstacle removal, and ancestral use cases.

3. Add a minimal verification loop with 3-5 fixed backtest weeks and inspect whether the chosen verses change for the right reasons; if not, adjust weights and tags before adding any new interface.
