"""Export MLflow notification runs and janam patri to JSON for the dashboard."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
EXPERIMENT_NAME = "vedic-wisdom-weekly"
DASHBOARD_DATA = Path(__file__).resolve().parent.parent / "dashboard" / "data"


def _keep_or_write_empty_runs() -> int:
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    path = DASHBOARD_DATA / "recommendations.json"
    if not path.exists():
        path.write_text("[]")
    return 0


def _run_to_dict(run) -> dict:
    params = run.data.params or {}
    metrics = run.data.metrics or {}
    return {
        "run_id": run.info.run_id,
        "week": params.get("week", ""),
        "verse_id": params.get("verse_id", ""),
        "verse_source": params.get("verse_source", ""),
        "observances": params.get("observances", ""),
        "observance_count": int(metrics.get("observance_count", 0)),
        "search_latency_ms": float(metrics.get("search_latency_ms", 0)),
        "start_time": str(run.info.start_time) if run.info.start_time else "",
    }


def export_runs() -> int:
    """Export all notification runs via MlflowClient. Returns count."""
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        mlflow.set_tracking_uri(TRACKING_URI)
        client = MlflowClient()
        exp = client.get_experiment_by_name(EXPERIMENT_NAME)
    except Exception as e:
        print(f"MLflow unavailable ({type(e).__name__}); keeping existing recommendations.json")
        return _keep_or_write_empty_runs()
    if not exp:
        return _keep_or_write_empty_runs()

    runs = client.search_runs(experiment_ids=[exp.experiment_id], order_by=["start_time DESC"])
    (DASHBOARD_DATA / "recommendations.json").write_text(json.dumps([_run_to_dict(r) for r in runs], indent=2))
    return len(runs)


def export_janam_patri() -> bool:
    """Export janam patri recommendations to dashboard/data/janam_patri.json. Returns True if written."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from janam_patri import run_to_dict

    root = Path(__file__).resolve().parent.parent
    data = run_to_dict(root / "config.yaml")
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    if not data:
        return False
    (DASHBOARD_DATA / "janam_patri.json").write_text(json.dumps(data, indent=2))
    return True


def export_current_digest() -> bool:
    """Export this week's canonical guidance to dashboard/data/current_digest.json."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from weekly_guidance import build_week, week_to_dict
    import datetime as dt

    days, chart, loc = build_week(dt.date.today(), write_history=False)
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    (DASHBOARD_DATA / "current_digest.json").write_text(json.dumps(week_to_dict(days, chart, loc), indent=2))
    return True


def main() -> None:
    n = export_runs()
    jp = export_janam_patri()
    export_current_digest()
    print(f"Exported {n} runs to {DASHBOARD_DATA / 'recommendations.json'}")
    if jp:
        print(f"Exported janam patri to {DASHBOARD_DATA / 'janam_patri.json'}")
    print(f"Exported current week panchang to {DASHBOARD_DATA / 'current_digest.json'}")


if __name__ == "__main__":
    main()
