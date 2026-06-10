from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from career_insight.config.settings import Settings, get_settings
from career_insight.data_processing.standardizer import clean_text, parse_salary_text


@dataclass
class CrawlResult:
    jobs: list[dict[str, Any]]
    visited_urls: list[str]
    errors: list[str]


class SlowJobScraper:
    """A conservative scraper for public job pages.

    It does not bypass login, captcha, anti-bot controls, or private APIs.
    Configure explicit target pages through CRAWL_TARGET_URLS.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.settings.crawl_user_agent})

    def crawl(self) -> CrawlResult:
        visited: list[str] = []
        errors: list[str] = []
        jobs: list[dict[str, Any]] = []

        urls = list(self.settings.crawl_target_urls)[: self.settings.crawl_max_pages]
        for index, url in enumerate(urls, start=1):
            try:
                html = self._load_url(url)
                visited.append(url)
                page_jobs = self._parse_jobs(html, url)
                jobs.extend(page_jobs)
            except Exception as exc:
                errors.append(f"{url}: {exc}")

            if index < len(urls):
                time.sleep(self.settings.crawl_delay_seconds)

        return CrawlResult(jobs=jobs, visited_urls=visited, errors=errors)

    def _load_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            return Path(parsed.path).read_text(encoding="utf-8")
        if parsed.scheme == "" and Path(url).exists():
            return Path(url).read_text(encoding="utf-8")

        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        return response.text

    def _parse_jobs(self, html: str, source_url: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = self._parse_json_ld(soup, source_url)
        if jobs:
            return jobs
        return self._parse_visible_cards(soup, source_url)

    def _parse_json_ld(self, soup: BeautifulSoup, source_url: str) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            text = script.string or script.get_text(strip=True)
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue

            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                jobs.extend(self._jobs_from_json_item(item, source_url))
        return jobs

    def _jobs_from_json_item(self, item: Any, source_url: str) -> list[dict[str, Any]]:
        if not isinstance(item, dict):
            return []
        if "@graph" in item and isinstance(item["@graph"], list):
            jobs: list[dict[str, Any]] = []
            for child in item["@graph"]:
                jobs.extend(self._jobs_from_json_item(child, source_url))
            return jobs

        item_type = item.get("@type")
        if isinstance(item_type, list):
            is_job = "JobPosting" in item_type
        else:
            is_job = item_type == "JobPosting"
        if not is_job:
            return []

        company = item.get("hiringOrganization") or {}
        location = item.get("jobLocation") or {}
        address = location.get("address") if isinstance(location, dict) else {}
        base_salary = item.get("baseSalary") or {}
        salary_text = self._salary_from_json(base_salary) or clean_text(item.get("salaryCurrency"))
        salary_min, salary_max = parse_salary_text(salary_text)

        return [
            {
                "job_title": clean_text(item.get("title"), "未知岗位"),
                "company_name": clean_text(company.get("name") if isinstance(company, dict) else company, "未知公司"),
                "city": clean_text(
                    address.get("addressLocality") if isinstance(address, dict) else "",
                    "未知",
                ),
                "district": clean_text(address.get("streetAddress") if isinstance(address, dict) else ""),
                "salary_text": salary_text or "面议",
                "salary_min": salary_min,
                "salary_max": salary_max,
                "education": clean_text(item.get("educationRequirements"), "不限"),
                "experience": clean_text(item.get("experienceRequirements"), "不限"),
                "skills": clean_text(item.get("skills") or item.get("qualifications")),
                "industry": clean_text(item.get("industry"), "未知"),
                "source": "web",
                "source_url": clean_text(item.get("url"), source_url),
            }
        ]

    def _salary_from_json(self, base_salary: Any) -> str:
        if not isinstance(base_salary, dict):
            return ""
        value = base_salary.get("value")
        if isinstance(value, dict):
            min_value = value.get("minValue")
            max_value = value.get("maxValue")
            unit = clean_text(value.get("unitText"))
            if min_value and max_value:
                suffix = "K" if unit.upper() in {"MONTH", "MON"} else ""
                return f"{min_value}-{max_value}{suffix}"
        if value:
            return str(value)
        return ""

    def _parse_visible_cards(self, soup: BeautifulSoup, source_url: str) -> list[dict[str, Any]]:
        candidates = soup.select(
            "[class*=job], [class*=position], [class*=职位], [class*=岗位], article, li"
        )
        jobs: list[dict[str, Any]] = []
        for index, node in enumerate(candidates[:80], start=1):
            text = clean_text(node.get_text(" ", strip=True))
            if not self._looks_like_job(text):
                continue

            title = self._first_text(
                node,
                [
                    "[class*=title]",
                    "[class*=name]",
                    "h1",
                    "h2",
                    "h3",
                    "a",
                ],
            )
            salary_text = self._match_salary(text) or "面议"
            salary_min, salary_max = parse_salary_text(salary_text)
            city = self._match_city(text)
            company = self._first_text(node, ["[class*=company]", "[class*=corp]", "[class*=企业]"])
            href = self._first_href(node) or f"{source_url}#job-{index}"

            jobs.append(
                {
                    "job_title": title or "未知岗位",
                    "company_name": company or "未知公司",
                    "city": city or "未知",
                    "district": "",
                    "salary_text": salary_text,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "education": self._match_choice(text, ["博士", "硕士", "本科", "大专", "学历不限"]) or "不限",
                    "experience": self._match_experience(text),
                    "skills": self._match_skills(text),
                    "industry": "未知",
                    "source": "web",
                    "source_url": href,
                }
            )
        return jobs

    def _looks_like_job(self, text: str) -> bool:
        if len(text) < 12:
            return False
        keywords = set(self.settings.crawl_keywords)
        return any(keyword in text for keyword in keywords) or bool(self._match_salary(text))

    def _first_text(self, node: Any, selectors: list[str]) -> str:
        for selector in selectors:
            found = node.select_one(selector)
            if found:
                value = clean_text(found.get_text(" ", strip=True))
                if value:
                    return value[:100]
        return ""

    def _first_href(self, node: Any) -> str:
        found = node.select_one("a[href]")
        if not found:
            return ""
        return clean_text(found.get("href"))

    def _match_salary(self, text: str) -> str:
        match = re.search(r"\d+(?:\.\d+)?\s*[-~]\s*\d+(?:\.\d+)?\s*[Kk千万wW]+(?:/月|·\d+薪)?", text)
        if match:
            return match.group(0)
        match = re.search(r"\d+(?:\.\d+)?\s*[Kk千万wW]+(?:/月)?", text)
        return match.group(0) if match else ""

    def _match_city(self, text: str) -> str:
        cities = [
            "北京",
            "上海",
            "广州",
            "深圳",
            "杭州",
            "南京",
            "成都",
            "武汉",
            "西安",
            "苏州",
            "天津",
            "重庆",
        ]
        return self._match_choice(text, cities)

    def _match_choice(self, text: str, choices: list[str]) -> str:
        for choice in choices:
            if choice in text:
                return choice
        return ""

    def _match_experience(self, text: str) -> str:
        match = re.search(r"\d+\s*[-~]\s*\d+\s*年", text)
        if match:
            return match.group(0)
        if any(token in text for token in ["应届", "实习", "在校"]):
            return "在校/应届"
        if "经验不限" in text:
            return "不限"
        return "不限"

    def _match_skills(self, text: str) -> str:
        skills = [
            "Python",
            "Spark",
            "Hive",
            "SQL",
            "Hadoop",
            "Flink",
            "Java",
            "Scala",
            "Pandas",
            "MySQL",
            "ETL",
            "Linux",
            "ECharts",
        ]
        found = [skill for skill in skills if skill.lower() in text.lower()]
        return ",".join(found)
