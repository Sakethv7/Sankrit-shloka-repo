"""Export MLflow notification runs and janam patri to JSON for the dashboard."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
EXPERIMENT_NAME = "vedic-wisdom-weekly"
DASHBOARD_DATA = Path(__file__).resolve().parent.parent / "dashboard" / "data"


def export_runs() -> int:
    """Export all notification runs via MlflowClient. Returns count."""
    mlflow.set_tracking_uri(TRACKING_URI)
    client = MlflowClient()
    exp = client.get_experiment_by_name(EXPERIMENT_NAME)
    if not exp:
        DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
        (DASHBOARD_DATA / "recommendations.json").write_text("[]")
        return 0

    runs = client.search_runs(experiment_ids=[exp.experiment_id], order_by=["start_time DESC"])
    out = []
    for run in runs:
        params = run.data.params or {}
        metrics = run.data.metrics or {}
        out.append({
            "run_id": run.info.run_id,
            "week": params.get("week", ""),
            "verse_id": params.get("verse_id", ""),
            "verse_source": params.get("verse_source", ""),
            "observances": params.get("observances", ""),
            "observance_count": int(metrics.get("observance_count", 0)),
            "search_latency_ms": float(metrics.get("search_latency_ms", 0)),
            "start_time": str(run.info.start_time) if run.info.start_time else "",
        })

    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    (DASHBOARD_DATA / "recommendations.json").write_text(json.dumps(out, indent=2))
    return len(out)


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


def main() -> None:
    n = export_runs()
    jp = export_janam_patri()
    print(f"Exported {n} runs to {DASHBOARD_DATA / 'recommendations.json'}")
    if jp:
        print(f"Exported janam patri to {DASHBOARD_DATA / 'janam_patri.json'}")


if __name__ == "__main__":
    main()
