from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from career_insight.data_processing.standardizer import split_skills
from career_insight.storage.mysql_handler import MySQLStore


def _decimal_to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analyze_jobs(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    city_salary_sum: dict[str, float] = defaultdict(float)
    city_salary_count: Counter[str] = Counter()
    city_job_count: Counter[str] = Counter()
    skill_counter: Counter[str] = Counter()
    education_counter: Counter[str] = Counter()
    experience_counter: Counter[str] = Counter()
    industry_counter: Counter[str] = Counter()

    salary_values: list[float] = []
    for job in jobs:
        city = str(job.get("city") or "未知")
        city_job_count[city] += 1

        salary_avg = _decimal_to_float(job.get("salary_avg"))
        if salary_avg is not None:
            city_salary_sum[city] += salary_avg
            city_salary_count[city] += 1
            salary_values.append(salary_avg)

        for skill in split_skills(job.get("skills")):
            skill_counter[skill] += 1

        education_counter[str(job.get("education") or "不限")] += 1
        experience_counter[str(job.get("experience") or "不限")] += 1
        industry_counter[str(job.get("industry") or "未知")] += 1

    city_salary = []
    for city, job_count in city_job_count.items():
        salary_count = city_salary_count.get(city, 0)
        avg_salary = (
            round(city_salary_sum[city] / salary_count, 2) if salary_count else None
        )
        city_salary.append(
            {"city": city, "job_count": int(job_count), "avg_salary": avg_salary}
        )
    city_salary.sort(key=lambda row: (row["avg_salary"] is not None, row["avg_salary"] or 0), reverse=True)

    metrics = {
        "total_jobs": len(jobs),
        "avg_salary": round(sum(salary_values) / len(salary_values), 2) if salary_values else None,
        "city_salary": city_salary,
        "skill_hotness": [
            {"skill": skill, "job_count": int(count)}
            for skill, count in skill_counter.most_common(20)
        ],
        "education_distribution": [
            {"education": name, "job_count": int(count)}
            for name, count in education_counter.most_common()
        ],
        "experience_distribution": [
            {"experience": name, "job_count": int(count)}
            for name, count in experience_counter.most_common()
        ],
        "industry_distribution": [
            {"industry": name, "job_count": int(count)}
            for name, count in industry_counter.most_common(10)
        ],
    }
    return metrics


def run_salary_and_trend_analysis(
    run_id: int,
    jobs: list[dict[str, Any]],
    store: MySQLStore,
) -> dict[str, Any]:
    metrics = analyze_jobs(jobs)
    store.replace_analysis(run_id, metrics)
    return metrics
