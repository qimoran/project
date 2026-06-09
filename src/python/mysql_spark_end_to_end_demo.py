from __future__ import annotations

import pymysql
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, count, round


MYSQL_HOST = "mysql"
MYSQL_PORT = 3306
MYSQL_USER = "zhitu"
MYSQL_PASSWORD = "zhitu123456"
MYSQL_DATABASE = "zhitu"
MYSQL_JAR = "/workspace/docker/build-context/assets/mysql-connector-j-8.0.33.jar"


RAW_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS demo_raw_jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_title VARCHAR(100) NOT NULL,
    company_name VARCHAR(150) NOT NULL,
    city VARCHAR(50) NOT NULL,
    salary_text VARCHAR(50) NOT NULL,
    salary_min DECIMAL(10, 2) NOT NULL,
    salary_max DECIMAL(10, 2) NOT NULL,
    education VARCHAR(50),
    experience VARCHAR(50),
    skills VARCHAR(255),
    source_url VARCHAR(255) UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


MOCK_JOBS = [
    (
        "大数据开发实习生",
        "上海云舟科技有限公司",
        "上海",
        "8-12K",
        8.00,
        12.00,
        "本科",
        "在校/应届",
        "Python,Spark,Hive,SQL",
        "mock://demo/001",
    ),
    (
        "数据分析师",
        "杭州数智信息技术有限公司",
        "杭州",
        "10-15K",
        10.00,
        15.00,
        "本科",
        "1-3年",
        "Python,Pandas,MySQL,ECharts",
        "mock://demo/002",
    ),
    (
        "数据仓库工程师",
        "北京星河数据有限公司",
        "北京",
        "15-25K",
        15.00,
        25.00,
        "本科",
        "3-5年",
        "Hive,Spark,ETL,Hadoop",
        "mock://demo/003",
    ),
]


def prepare_mysql_data() -> None:
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(RAW_TABLE_SQL)
            cursor.executemany(
                """
                INSERT INTO demo_raw_jobs (
                    job_title, company_name, city, salary_text,
                    salary_min, salary_max, education, experience,
                    skills, source_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    job_title = VALUES(job_title),
                    company_name = VALUES(company_name),
                    city = VALUES(city),
                    salary_text = VALUES(salary_text),
                    salary_min = VALUES(salary_min),
                    salary_max = VALUES(salary_max),
                    education = VALUES(education),
                    experience = VALUES(experience),
                    skills = VALUES(skills);
                """,
                MOCK_JOBS,
            )
            cursor.execute("DROP TABLE IF EXISTS demo_clean_jobs;")
            cursor.execute(
                """
                CREATE TABLE demo_clean_jobs AS
                SELECT
                    id AS raw_id,
                    job_title,
                    company_name,
                    city,
                    salary_text,
                    salary_min,
                    salary_max,
                    ROUND((salary_min + salary_max) / 2, 2) AS salary_avg,
                    education,
                    experience,
                    skills
                FROM demo_raw_jobs;
                """
            )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    prepare_mysql_data()
    print("MySQL demo_raw_jobs 和 demo_clean_jobs 已准备完成")

    spark = (
        SparkSession.builder.appName("mysql-spark-end-to-end-demo")
        .master("spark://spark-master:7077")
        .config("spark.jars", MYSQL_JAR)
        .getOrCreate()
    )

    jdbc_url = (
        f"jdbc:mysql://{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        "?useSSL=false&allowPublicKeyRetrieval=true"
        "&serverTimezone=Asia/Shanghai&characterEncoding=utf8"
    )
    props = {
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "driver": "com.mysql.cj.jdbc.Driver",
    }

    try:
        jobs = spark.read.jdbc(url=jdbc_url, table="demo_clean_jobs", properties=props)

        print("Spark 读取 MySQL demo_clean_jobs：")
        jobs.show(truncate=False)

        city_salary = (
            jobs.groupBy("city")
            .agg(
                count("*").alias("job_count"),
                round(avg("salary_avg"), 2).alias("avg_salary"),
            )
            .orderBy("avg_salary", ascending=False)
        )

        print("Spark 城市平均薪资分析结果：")
        city_salary.show(truncate=False)

        city_salary.write.jdbc(
            url=jdbc_url,
            table="demo_city_salary_spark",
            mode="overwrite",
            properties=props,
        )
        print("分析结果已写回 MySQL：demo_city_salary_spark")

        city_salary.write.mode("overwrite").option("header", "true").csv(
            "hdfs://namenode:9000/user/zhitu/demo/city_salary_spark"
        )
        print("分析结果已写入 HDFS：/user/zhitu/demo/city_salary_spark")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
