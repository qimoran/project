from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from career_insight.config.database import get_mysql_connection
from career_insight.config.settings import Settings, get_settings


def _json_default(value: Any) -> str | float:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    return str(value)


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


class MySQLStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _connect(self, *, autocommit: bool = True):
        return get_mysql_connection(self.settings, autocommit=autocommit)

    def ensure_schema(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS raw_jobs (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                job_title VARCHAR(100) NOT NULL COMMENT '职位名称',
                company_name VARCHAR(150) NOT NULL COMMENT '公司名称',
                city VARCHAR(50) NOT NULL COMMENT '工作城市',
                district VARCHAR(50) NULL COMMENT '工作区域',
                salary_text VARCHAR(50) NOT NULL COMMENT '原始薪资文本',
                salary_min DECIMAL(10, 2) NULL COMMENT '月薪下限，单位：千元',
                salary_max DECIMAL(10, 2) NULL COMMENT '月薪上限，单位：千元',
                education VARCHAR(50) NULL COMMENT '学历要求',
                experience VARCHAR(50) NULL COMMENT '经验要求',
                skills VARCHAR(255) NULL COMMENT '技能关键词',
                industry VARCHAR(100) NULL COMMENT '公司行业',
                source VARCHAR(50) NOT NULL DEFAULT 'agent' COMMENT '数据来源',
                source_url VARCHAR(255) NOT NULL COMMENT '来源链接或模拟编号',
                crawled_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_raw_jobs_source_url (source_url),
                KEY idx_raw_jobs_city (city),
                KEY idx_raw_jobs_job_title (job_title)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_clean_jobs (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                raw_id BIGINT NULL,
                job_title VARCHAR(100) NOT NULL,
                company_name VARCHAR(150) NOT NULL,
                city VARCHAR(50) NOT NULL,
                district VARCHAR(50) NULL,
                salary_text VARCHAR(50) NULL,
                salary_min DECIMAL(10, 2) NULL,
                salary_max DECIMAL(10, 2) NULL,
                salary_avg DECIMAL(10, 2) NULL,
                education VARCHAR(50) NULL,
                experience VARCHAR(50) NULL,
                skills VARCHAR(255) NULL,
                industry VARCHAR(100) NULL,
                source VARCHAR(50) NULL,
                source_url VARCHAR(255) NULL,
                cleaned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_agent_clean_jobs_source_url (source_url),
                KEY idx_agent_clean_jobs_city (city),
                KEY idx_agent_clean_jobs_salary_avg (salary_avg)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                trigger_type VARCHAR(30) NOT NULL,
                status VARCHAR(30) NOT NULL,
                message TEXT NULL,
                raw_count INT NOT NULL DEFAULT 0,
                clean_count INT NOT NULL DEFAULT 0,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY idx_agent_runs_status (status),
                KEY idx_agent_runs_started_at (started_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_run_steps (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                run_id BIGINT NOT NULL,
                step_name VARCHAR(80) NOT NULL,
                status VARCHAR(30) NOT NULL,
                detail TEXT NULL,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP NULL,
                KEY idx_agent_run_steps_run_id (run_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_reports (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                run_id BIGINT NOT NULL,
                title VARCHAR(200) NOT NULL,
                report_markdown MEDIUMTEXT NOT NULL,
                metrics_json JSON NOT NULL,
                llm_model VARCHAR(120) NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY idx_agent_reports_run_id (run_id),
                KEY idx_agent_reports_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_schedule (
                id TINYINT PRIMARY KEY,
                enabled TINYINT(1) NOT NULL DEFAULT 0,
                daily_time VARCHAR(5) NOT NULL DEFAULT '09:00',
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_analysis_city_salary (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                run_id BIGINT NOT NULL,
                city VARCHAR(50) NOT NULL,
                job_count INT NOT NULL,
                avg_salary DECIMAL(10, 2) NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY idx_analysis_city_salary_run_id (run_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_analysis_skill_hotness (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                run_id BIGINT NOT NULL,
                skill VARCHAR(80) NOT NULL,
                job_count INT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY idx_analysis_skill_hotness_run_id (run_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_analysis_education_distribution (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                run_id BIGINT NOT NULL,
                education VARCHAR(80) NOT NULL,
                job_count INT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY idx_analysis_education_distribution_run_id (run_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_analysis_experience_distribution (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                run_id BIGINT NOT NULL,
                experience VARCHAR(80) NOT NULL,
                job_count INT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY idx_analysis_experience_distribution_run_id (run_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
        ]

        with self._connect() as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
                cursor.execute(
                    """
                    INSERT IGNORE INTO agent_schedule (id, enabled, daily_time)
                    VALUES (1, 0, '09:00')
                    """
                )

    def create_run(self, trigger_type: str) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_runs (trigger_type, status, message)
                    VALUES (%s, 'running', %s)
                    """,
                    (trigger_type, "流程智能体开始运行"),
                )
                return int(cursor.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        message: str,
        raw_count: int = 0,
        clean_count: int = 0,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE agent_runs
                    SET status=%s, message=%s, raw_count=%s, clean_count=%s, finished_at=NOW()
                    WHERE id=%s
                    """,
                    (status, message, raw_count, clean_count, run_id),
                )

    def start_step(self, run_id: int, step_name: str, detail: str = "") -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_run_steps (run_id, step_name, status, detail)
                    VALUES (%s, %s, 'running', %s)
                    """,
                    (run_id, step_name, detail),
                )
                return int(cursor.lastrowid)

    def finish_step(self, step_id: int, status: str, detail: str = "") -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE agent_run_steps
                    SET status=%s, detail=%s, finished_at=NOW()
                    WHERE id=%s
                    """,
                    (status, detail, step_id),
                )

    def insert_raw_jobs(self, jobs: list[dict[str, Any]]) -> int:
        if not jobs:
            return 0

        columns = [
            "job_title",
            "company_name",
            "city",
            "district",
            "salary_text",
            "salary_min",
            "salary_max",
            "education",
            "experience",
            "skills",
            "industry",
            "source",
            "source_url",
        ]
        placeholders = ", ".join(["%s"] * len(columns))
        update_clause = ", ".join(
            f"{column}=VALUES({column})" for column in columns if column != "source_url"
        )
        sql = f"""
            INSERT INTO raw_jobs ({", ".join(columns)})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}, updated_at=CURRENT_TIMESTAMP
        """

        with self._connect() as conn:
            with conn.cursor() as cursor:
                affected = cursor.executemany(
                    sql,
                    [[job.get(column) for column in columns] for job in jobs],
                )
                return int(affected)

    def fetch_raw_jobs(self, limit: int = 1000) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        job_title,
                        company_name,
                        city,
                        district,
                        salary_text,
                        salary_min,
                        salary_max,
                        education,
                        experience,
                        skills,
                        industry,
                        source,
                        source_url,
                        crawled_at
                    FROM raw_jobs
                    ORDER BY crawled_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return list(cursor.fetchall())

    def replace_clean_jobs(self, jobs: list[dict[str, Any]]) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM agent_clean_jobs")
                if not jobs:
                    return 0

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
                placeholders = ", ".join(["%s"] * len(columns))
                cursor.executemany(
                    f"""
                    INSERT INTO agent_clean_jobs ({", ".join(columns)})
                    VALUES ({placeholders})
                    """,
                    [[job.get(column) for column in columns] for job in jobs],
                )
                return int(cursor.rowcount)

    def fetch_clean_jobs(self, limit: int = 2000) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM agent_clean_jobs
                    ORDER BY cleaned_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return list(cursor.fetchall())

    def replace_analysis(self, run_id: int, metrics: dict[str, Any]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                for table in [
                    "agent_analysis_city_salary",
                    "agent_analysis_skill_hotness",
                    "agent_analysis_education_distribution",
                    "agent_analysis_experience_distribution",
                ]:
                    cursor.execute(f"DELETE FROM {table} WHERE run_id=%s", (run_id,))

                cursor.executemany(
                    """
                    INSERT INTO agent_analysis_city_salary (run_id, city, job_count, avg_salary)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [
                        (run_id, row["city"], row["job_count"], row["avg_salary"])
                        for row in metrics.get("city_salary", [])
                    ],
                )
                cursor.executemany(
                    """
                    INSERT INTO agent_analysis_skill_hotness (run_id, skill, job_count)
                    VALUES (%s, %s, %s)
                    """,
                    [
                        (run_id, row["skill"], row["job_count"])
                        for row in metrics.get("skill_hotness", [])
                    ],
                )
                cursor.executemany(
                    """
                    INSERT INTO agent_analysis_education_distribution (run_id, education, job_count)
                    VALUES (%s, %s, %s)
                    """,
                    [
                        (run_id, row["education"], row["job_count"])
                        for row in metrics.get("education_distribution", [])
                    ],
                )
                cursor.executemany(
                    """
                    INSERT INTO agent_analysis_experience_distribution (run_id, experience, job_count)
                    VALUES (%s, %s, %s)
                    """,
                    [
                        (run_id, row["experience"], row["job_count"])
                        for row in metrics.get("experience_distribution", [])
                    ],
                )

    def save_report(
        self,
        run_id: int,
        *,
        title: str,
        report_markdown: str,
        metrics: dict[str, Any],
        llm_model: str,
    ) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_reports (run_id, title, report_markdown, metrics_json, llm_model)
                    VALUES (%s, %s, %s, CAST(%s AS JSON), %s)
                    """,
                    (run_id, title, report_markdown, dumps_json(metrics), llm_model),
                )
                return int(cursor.lastrowid)

    def latest_run(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM agent_runs ORDER BY id DESC LIMIT 1")
                return cursor.fetchone()

    def latest_report(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM agent_reports ORDER BY id DESC LIMIT 1")
                return cursor.fetchone()

    def run_steps(self, run_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM agent_run_steps
                    WHERE run_id=%s
                    ORDER BY id
                    """,
                    (run_id,),
                )
                return list(cursor.fetchall())

    def latest_analysis(self) -> dict[str, list[dict[str, Any]]]:
        latest = self.latest_report()
        if not latest:
            return {
                "city_salary": [],
                "skill_hotness": [],
                "education_distribution": [],
                "experience_distribution": [],
            }

        run_id = latest["run_id"]
        queries = {
            "city_salary": """
                SELECT city, job_count, avg_salary
                FROM agent_analysis_city_salary
                WHERE run_id=%s
                ORDER BY avg_salary DESC, job_count DESC
            """,
            "skill_hotness": """
                SELECT skill, job_count
                FROM agent_analysis_skill_hotness
                WHERE run_id=%s
                ORDER BY job_count DESC, skill
                LIMIT 20
            """,
            "education_distribution": """
                SELECT education, job_count
                FROM agent_analysis_education_distribution
                WHERE run_id=%s
                ORDER BY job_count DESC
            """,
            "experience_distribution": """
                SELECT experience, job_count
                FROM agent_analysis_experience_distribution
                WHERE run_id=%s
                ORDER BY job_count DESC
            """,
        }

        result: dict[str, list[dict[str, Any]]] = {}
        with self._connect() as conn:
            with conn.cursor() as cursor:
                for key, sql in queries.items():
                    cursor.execute(sql, (run_id,))
                    result[key] = list(cursor.fetchall())
        return result

    def get_schedule(self) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT enabled, daily_time FROM agent_schedule WHERE id=1")
                row = cursor.fetchone()
                if not row:
                    return {"enabled": False, "daily_time": "09:00"}
                return {"enabled": bool(row["enabled"]), "daily_time": row["daily_time"]}

    def set_schedule(self, enabled: bool, daily_time: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_schedule (id, enabled, daily_time)
                    VALUES (1, %s, %s)
                    ON DUPLICATE KEY UPDATE enabled=VALUES(enabled), daily_time=VALUES(daily_time)
                    """,
                    (1 if enabled else 0, daily_time),
                )
