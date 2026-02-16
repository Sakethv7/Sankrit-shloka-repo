# Vedic Wisdom Dashboard

View your **tithi-based weekly shlokas**, **janam patri recommendations**, and **insights** from past digests.

## What it shows

- **Janam Patri** — Birth place, janma nakshatra, rashi, and recommended shlokas (from your birth chart).
- **Insights** — Weeks tracked, total observances, most recommended verse, most frequent observance.
- **Weekly recommendation history** — Each week’s verse and observances (from MLflow).

## How to run the dashboard

### 1. Export data (required first)

From the **project root** (Sankrit-shloka-repo):

```bash
python scripts/export_mlflow_runs.py
```

This writes:

- `dashboard/data/recommendations.json` — weekly digest runs from MLflow.
- `dashboard/data/janam_patri.json` — birth chart and recommended verses (if janam patri is enabled in `config.yaml`).

Run this again whenever you generate a new weekly digest or change janam patri settings.

### 2. Serve the dashboard

From the project root:

```bash
python scripts/serve_dashboard.py
```

This starts a local server (default port **8080**) and opens `http://localhost:8080/` in your browser.

To use a different port:

```bash
DASHBOARD_PORT=3000 python scripts/serve_dashboard.py
```

### Alternative: serve without the script

From the **dashboard** directory:

```bash
cd dashboard
python -m http.server 8080
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

Or use Node if you have it:

```bash
cd dashboard
npx serve .
```

Then open the URL it prints (e.g. http://localhost:3000).

## End-to-end flow

1. **Weekly digest (tithi-aware shlokas, EST)**  
   `python scripts/weekly_notification.py`  
   Generates the week’s panchang, observances, and one shloka per tithi; logs to MLflow.

2. **Janam patri recommendations**  
   `python scripts/janam_patri.py`  
   Prints birth nakshatra, rashi, and recommended verses. Same data is exported when you run the export script.

3. **Export for dashboard**  
   `python scripts/export_mlflow_runs.py`  
   Updates `dashboard/data/recommendations.json` and `dashboard/data/janam_patri.json`.

4. **View dashboard**  
   `python scripts/serve_dashboard.py`  
   Open the dashboard in the browser to see janam patri, insights, and history.
