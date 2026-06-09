from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

import pymysql


CREATE_TABLE_SQL = """
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
    source VARCHAR(50) NOT NULL DEFAULT 'mock' COMMENT '数据来源',
    source_url VARCHAR(255) NOT NULL COMMENT '来源链接或模拟编号',
    crawled_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_raw_jobs_source_url (source_url),
    KEY idx_raw_jobs_city (city),
    KEY idx_raw_jobs_job_title (job_title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


MOCK_JOBS = [
    {
        "job_title": "大数据开发实习生",
        "company_name": "上海云舟科技有限公司",
        "city": "上海",
        "district": "浦东新区",
        "salary_text": "8-12K",
        "salary_min": Decimal("8.00"),
        "salary_max": Decimal("12.00"),
        "education": "本科",
        "experience": "在校/应届",
        "skills": "Python,Spark,Hive,SQL",
        "industry": "互联网",
        "source": "mock",
        "source_url": "mock://job/001",
    },
    {
        "job_title": "数据分析师",
        "company_name": "杭州数智信息技术有限公司",
        "city": "杭州",
        "district": "西湖区",
        "salary_text": "10-15K",
        "salary_min": Decimal("10.00"),
        "salary_max": Decimal("15.00"),
        "education": "本科",
        "experience": "1-3年",
        "skills": "Python,Pandas,MySQL,ECharts",
        "industry": "数据服务",
        "source": "mock",
        "source_url": "mock://job/002",
    },
    {
        "job_title": "数据仓库工程师",
        "company_name": "北京星河数据有限公司",
        "city": "北京",
        "district": "海淀区",
        "salary_text": "15-25K",
        "salary_min": Decimal("15.00"),
        "salary_max": Decimal("25.00"),
        "education": "本科",
        "experience": "3-5年",
        "skills": "Hive,Spark,ETL,Hadoop",
        "industry": "软件服务",
        "source": "mock",
        "source_url": "mock://job/003",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create raw_jobs and insert 3 mock jobs.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "mysql"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "zhitu"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD", "zhitu123456"))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE", "zhitu"))
    return parser.parse_args()


def connect(args: argparse.Namespace) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def seed_mock_jobs(conn: pymysql.connections.Connection) -> None:
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

    insert_sql = f"""
    INSERT INTO raw_jobs ({", ".join(columns)})
    VALUES ({placeholders})
    ON DUPLICATE KEY UPDATE {update_clause};
    """

    with conn.cursor() as cursor:
        cursor.execute(CREATE_TABLE_SQL)
        cursor.executemany(
            insert_sql,
            [[job[column] for column in columns] for job in MOCK_JOBS],
        )
    conn.commit()


def print_seed_result(conn: pymysql.connections.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM raw_jobs;")
        total = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT
                id,
                job_title,
                company_name,
                city,
                salary_text,
                education,
                experience,
                skills
            FROM raw_jobs
            ORDER BY id;
            """
        )
        rows = cursor.fetchall()

    print(f"raw_jobs table is ready. total rows: {total}")
    print("mock rows:")
    for row in rows:
        print(
            f"- #{row['id']} {row['city']} | {row['job_title']} | "
            f"{row['company_name']} | {row['salary_text']} | {row['skills']}"
        )


def main() -> int:
    args = parse_args()
    try:
        conn = connect(args)
    except Exception as exc:
        print(f"Failed to connect MySQL: {exc}", file=sys.stderr)
        return 1

    try:
        seed_mock_jobs(conn)
        print_seed_result(conn)
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"Failed to seed mock jobs: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
