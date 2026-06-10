from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Iterable


_SKILL_ALIASES = {
    "python": "Python",
    "pyspark": "PySpark",
    "spark": "Spark",
    "hive": "Hive",
    "hadoop": "Hadoop",
    "mysql": "MySQL",
    "sql": "SQL",
    "flink": "Flink",
    "java": "Java",
    "scala": "Scala",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "echarts": "ECharts",
    "linux": "Linux",
    "etl": "ETL",
}


def clean_text(value: object, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text or default


def normalize_city(value: object) -> str:
    text = clean_text(value, "未知")
    text = re.sub(r"(市|地区|特别行政区)$", "", text)
    return text or "未知"


def normalize_education(value: object) -> str:
    text = clean_text(value, "不限")
    for token in ["博士", "硕士", "本科", "大专", "高中", "中专"]:
        if token in text:
            return token
    if "不限" in text or "无" in text:
        return "不限"
    return text


def normalize_experience(value: object) -> str:
    text = clean_text(value, "不限")
    if any(token in text for token in ["应届", "在校", "实习"]):
        return "在校/应届"
    if "不限" in text or "无" in text:
        return "不限"
    return text


def _to_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def parse_salary_text(value: object) -> tuple[Decimal | None, Decimal | None]:
    """Return monthly salary range in K RMB."""
    text = clean_text(value)
    if not text or "面议" in text:
        return None, None

    normalized = text.lower().replace(" ", "")
    multiplier = Decimal("1")
    if "万" in normalized and "年" not in normalized:
        multiplier = Decimal("10")
    elif "元" in normalized:
        multiplier = Decimal("0.001")

    numbers = re.findall(r"\d+(?:\.\d+)?", normalized)
    if not numbers:
        return None, None

    if "年" in normalized and ("万" in normalized or "w" in normalized):
        annual_to_monthly_k = Decimal("10") / Decimal("12")
        values = [Decimal(number) * annual_to_monthly_k for number in numbers[:2]]
    else:
        values = [Decimal(number) * multiplier for number in numbers[:2]]

    if len(values) == 1:
        min_salary = max_salary = values[0]
    else:
        min_salary, max_salary = values[0], values[1]
        if min_salary > max_salary:
            min_salary, max_salary = max_salary, min_salary

    return min_salary.quantize(Decimal("0.01")), max_salary.quantize(Decimal("0.01"))


def normalize_salary(
    salary_text: object,
    salary_min: object = None,
    salary_max: object = None,
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    min_value = _to_decimal(salary_min)
    max_value = _to_decimal(salary_max)
    if min_value is None or max_value is None:
        parsed_min, parsed_max = parse_salary_text(salary_text)
        min_value = min_value or parsed_min
        max_value = max_value or parsed_max

    if min_value is not None and max_value is not None:
        avg_value = ((min_value + max_value) / Decimal("2")).quantize(Decimal("0.01"))
    else:
        avg_value = None
    return min_value, max_value, avg_value


def normalize_skill(value: str) -> str:
    key = value.strip().lower()
    return _SKILL_ALIASES.get(key, value.strip())


def split_skills(value: object) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    parts = re.split(r"[,，/、;；\s]+", text)
    skills: list[str] = []
    seen: set[str] = set()
    for part in parts:
        skill = normalize_skill(part)
        if not skill:
            continue
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        skills.append(skill)
    return skills


def join_skills(values: Iterable[str]) -> str:
    return ",".join(split_skills(",".join(values)))
