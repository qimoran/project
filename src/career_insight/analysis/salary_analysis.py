from __future__ import annotations

from typing import Any

from career_insight.analysis.trend_analysis import analyze_jobs
from career_insight.storage.mysql_handler import MySQLStore


def run_salary_and_trend_analysis(
    run_id: int,
    jobs: list[dict[str, Any]],
    store: MySQLStore,
) -> dict[str, Any]:
    metrics = analyze_jobs(jobs)
    store.replace_analysis(run_id, metrics)
    return metrics
