from __future__ import annotations

from typing import Any

from career_insight.data_processing.standardizer import (
    clean_text,
    join_skills,
    normalize_city,
    normalize_education,
    normalize_experience,
    normalize_salary,
    split_skills,
)


def clean_job(row: dict[str, Any]) -> dict[str, Any] | None:
    job_title = clean_text(row.get("job_title"))
    company_name = clean_text(row.get("company_name"))
    city = normalize_city(row.get("city"))
    if not job_title or not company_name or not city:
        return None

    salary_text = clean_text(row.get("salary_text"), "面议")
    salary_min, salary_max, salary_avg = normalize_salary(
        salary_text,
        row.get("salary_min"),
        row.get("salary_max"),
    )
    skills = join_skills(split_skills(row.get("skills")))

    return {
        "raw_id": row.get("id") or row.get("raw_id"),
        "job_title": job_title,
        "company_name": company_name,
        "city": city,
        "district": clean_text(row.get("district")),
        "salary_text": salary_text,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_avg": salary_avg,
        "education": normalize_education(row.get("education")),
        "experience": normalize_experience(row.get("experience")),
        "skills": skills,
        "industry": clean_text(row.get("industry"), "未知"),
        "source": clean_text(row.get("source"), "agent"),
        "source_url": clean_text(row.get("source_url"), f"agent://raw/{row.get('id', '')}"),
    }


def clean_jobs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        item = clean_job(row)
        if not item:
            continue
        dedupe_key = item.get("source_url") or (
            item["job_title"],
            item["company_name"],
            item["city"],
        )
        if str(dedupe_key) in seen:
            continue
        seen.add(str(dedupe_key))
        cleaned.append(item)
    return cleaned
