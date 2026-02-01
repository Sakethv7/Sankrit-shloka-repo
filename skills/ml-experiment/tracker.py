"""MLflow experiment tracker for Vedic Wisdom Weekly.

Tracks verse search quality, notification generation metrics,
and embedding model experiments.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass

import mlflow

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
EXPERIMENT_NAME = "vedic-wisdom-weekly"


def _ensure_experiment() -> str:
    """Create or get the MLflow experiment, return experiment ID."""
    mlflow.set_tracking_uri(TRACKING_URI)
    exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    return exp.experiment_id if exp else mlflow.create_experiment(EXPERIMENT_NAME)


@dataclass
class SearchMetrics:
    query: str
    results_count: int
    top_score: float
    latency_ms: float


@contextmanager
def track_search(query: str):
    """Context manager to track a verse search run in MLflow."""
    _ensure_experiment()
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name=f"search-{query[:30]}"):
        metrics = SearchMetrics(query=query, results_count=0, top_score=0.0, latency_ms=0.0)
        yield metrics
        mlflow.log_param("query", query)
        mlflow.log_metrics({
            "results_count": metrics.results_count,
            "top_score": metrics.top_score,
            "latency_ms": metrics.latency_ms,
        })


def log_notification(
    week: str,
    observance_count: int,
    verse_id: str | None,
    *,
    observance_names: str = "",
    verse_source: str = "",
    search_query: str = "",
    search_latency_ms: float = 0.0,
    corpus_size: int = 0,
) -> None:
    """Log a weekly notification generation event with full context."""
    _ensure_experiment()
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name=f"notify-{week}"):
        mlflow.log_params({
            "week": week,
            "verse_id": verse_id or "none",
            "verse_source": verse_source or "none",
            "observances": observance_names or "none",
            "search_query": search_query[:250] or "none",
        })
        mlflow.log_metrics({
            "observance_count": observance_count,
            "search_latency_ms": search_latency_ms,
            "corpus_size": corpus_size,
        })


if __name__ == "__main__":
    log_notification("2025-W01", observance_count=3, verse_id="bg-2.47")
    print("Logged sample notification to MLflow.")
