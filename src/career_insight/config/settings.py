from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    mysql_host: str = os.getenv("MYSQL_HOST", "mysql")
    mysql_port: int = _get_int("MYSQL_PORT", 3306)
    mysql_user: str = os.getenv("MYSQL_USER", "zhitu")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "zhitu123456")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "zhitu")

    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = _get_int("REDIS_PORT", 6379)
    hadoop_fs: str = os.getenv("HADOOP_FS", "hdfs://namenode:9000")
    webhdfs_url: str = os.getenv("WEBHDFS_URL", "http://namenode:9870/webhdfs/v1")
    spark_master: str = os.getenv("SPARK_MASTER", "spark://spark-master:7077")

    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_timeout_seconds: int = _get_int("LLM_TIMEOUT_SECONDS", 60)

    crawl_target_urls: tuple[str, ...] = tuple(_split_csv(os.getenv("CRAWL_TARGET_URLS")))
    crawl_keywords: tuple[str, ...] = tuple(
        _split_csv(os.getenv("CRAWL_KEYWORDS", "大数据,数据分析,Spark,Hive"))
    )
    crawl_max_pages: int = _get_int("CRAWL_MAX_PAGES", 2)
    crawl_delay_seconds: float = _get_float("CRAWL_DELAY_SECONDS", 3.0)
    crawl_user_agent: str = os.getenv(
        "CRAWL_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36 CareerInsightBot/1.0",
    )

    agent_schedule_enabled: bool = _get_bool("AGENT_SCHEDULE_ENABLED", False)
    agent_daily_time: str = os.getenv("AGENT_DAILY_TIME", "09:00")

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url and self.llm_model)

    @property
    def mysql_dsn_label(self) -> str:
        return f"{self.mysql_user}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"


def get_settings() -> Settings:
    return Settings()


def as_text_list(items: Iterable[str]) -> str:
    values = [item for item in items if item]
    return ", ".join(values) if values else "未配置"
