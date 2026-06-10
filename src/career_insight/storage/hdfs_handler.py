from __future__ import annotations

import csv
import io
import json
from typing import Any

import requests

from career_insight.config.settings import Settings, get_settings


class WebHDFSClient:
    def __init__(self, settings: Settings | None = None, user: str = "root") -> None:
        self.settings = settings or get_settings()
        self.user = user
        self.base_url = self.settings.webhdfs_url.rstrip("/")

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def mkdirs(self, path: str) -> None:
        response = requests.put(
            self._url(path),
            params={"op": "MKDIRS", "user.name": self.user},
            timeout=10,
        )
        response.raise_for_status()

    def write_text(self, path: str, content: str) -> None:
        parent = path.rsplit("/", 1)[0] or "/"
        self.mkdirs(parent)
        response = requests.put(
            self._url(path),
            params={"op": "CREATE", "overwrite": "true", "user.name": self.user},
            allow_redirects=False,
            timeout=10,
        )
        response.raise_for_status()
        upload_url = response.headers["Location"]
        upload = requests.put(upload_url, data=content.encode("utf-8"), timeout=20)
        upload.raise_for_status()


def jobs_to_csv(jobs: list[dict[str, Any]]) -> str:
    columns = [
        "raw_id",
        "job_title",
        "company_name",
        "city",
        "district",
        "salary_text",
        "salary_min",
        "salary_max",
        "salary_avg",
        "education",
        "experience",
        "skills",
        "industry",
        "source",
        "source_url",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for job in jobs:
        writer.writerow({column: job.get(column, "") for column in columns})
    return buffer.getvalue()


def sync_agent_outputs(
    run_id: int,
    *,
    jobs: list[dict[str, Any]],
    metrics: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> list[str]:
    client = WebHDFSClient(settings)
    written: list[str] = []
    base_path = f"/user/zhitu/agent/run_{run_id}"

    clean_jobs_path = f"{base_path}/clean_jobs.csv"
    client.write_text(clean_jobs_path, jobs_to_csv(jobs))
    written.append(clean_jobs_path)

    if metrics is not None:
        metrics_path = f"{base_path}/metrics.json"
        client.write_text(metrics_path, json.dumps(metrics, ensure_ascii=False, default=str))
        written.append(metrics_path)

        latest_path = "/user/zhitu/agent/latest_metrics.json"
        client.write_text(latest_path, json.dumps(metrics, ensure_ascii=False, default=str))
        written.append(latest_path)

    return written
