from __future__ import annotations

import argparse
import socket
import sys
from contextlib import closing

import pymysql
import redis
import requests


def ok(name: str, detail: str) -> bool:
    print(f"[OK]   {name}: {detail}")
    return True


def fail(name: str, detail: str) -> bool:
    print(f"[FAIL] {name}: {detail}")
    return False


def check_tcp(name: str, host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with closing(socket.create_connection((host, port), timeout=timeout)):
            return ok(name, f"{host}:{port} reachable")
    except OSError as exc:
        return fail(name, f"{host}:{port} unreachable ({exc})")


def check_mysql(host: str, port: int, user: str, password: str) -> bool:
    name = "MySQL"
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5,
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                databases = [row[0] for row in cursor.fetchall()]
            return ok(name, "databases=" + ",".join(databases))
        finally:
            conn.close()
    except Exception as exc:
        return fail(name, str(exc))


def check_redis(host: str, port: int) -> bool:
    name = "Redis"
    try:
        client = redis.Redis(host=host, port=port, socket_connect_timeout=5, protocol=2)
        response = client.ping()
        return ok(name, f"PING={response}")
    except Exception as exc:
        return fail(name, str(exc))


def check_hdfs_webhdfs(host: str, port: int, user: str) -> bool:
    name = "HDFS WebHDFS"
    url = f"http://{host}:{port}/webhdfs/v1/?op=LISTSTATUS&user.name={user}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        statuses = data.get("FileStatuses", {}).get("FileStatus", [])
        paths = [item.get("pathSuffix", "") or "/" for item in statuses]
        return ok(name, "root entries=" + ",".join(paths))
    except Exception as exc:
        return fail(name, str(exc))


def check_spark_job(master: str) -> bool:
    name = "Spark job"
    try:
        from pyspark.sql import SparkSession

        spark = (
            SparkSession.builder.master(master)
            .appName("check-bigdata-connections")
            .getOrCreate()
        )
        try:
            count = spark.range(1, 6).count()
            if count != 5:
                return fail(name, f"unexpected count={count}")
            return ok(name, f"{master} range count={count}")
        finally:
            spark.stop()
    except Exception as exc:
        return fail(name, str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the local Docker bigdata stack.")
    parser.add_argument("--spark-job", action="store_true", help="Run a tiny Spark job.")
    args = parser.parse_args()

    checks = [
        check_tcp("MySQL TCP", "mysql", 3306),
        check_mysql("mysql", 3306, "root", "root123456"),
        check_tcp("Redis TCP", "redis", 6379),
        check_redis("redis", 6379),
        check_tcp("HDFS NameNode RPC", "namenode", 9000),
        check_tcp("HDFS NameNode Web", "namenode", 9870),
        check_hdfs_webhdfs("namenode", 9870, "root"),
        check_tcp("YARN ResourceManager Web", "resourcemanager", 8088),
        check_tcp("Hive Metastore TCP", "hive-metastore", 9083),
        check_tcp("HiveServer2 JDBC TCP", "hiveserver2", 10000),
        check_tcp("HiveServer2 Web TCP", "hiveserver2", 10002),
        check_tcp("Spark Master TCP", "spark-master", 7077),
        check_tcp("Spark Master Web", "spark-master", 8080),
        check_tcp("Spark Worker Web", "spark-worker", 8081),
    ]

    if args.spark_job:
        checks.append(check_spark_job("spark://spark-master:7077"))

    passed = sum(1 for item in checks if item)
    total = len(checks)
    print(f"\nResult: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
