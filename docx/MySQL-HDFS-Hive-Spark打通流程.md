# MySQL、HDFS、Hive、Spark 打通流程

本文档记录本项目从 MySQL 模拟数据开始，逐步打通 HDFS、Hive 和 Spark 的最小流程。

## 1. 已打通的链路

当前已经验证通过两条链路：

```text
链路一：
MySQL -> TSV 文件 -> HDFS -> Hive 外部表 -> Hive SQL 分析

链路二：
MySQL -> Spark JDBC 读取 -> Spark DataFrame 分析
```

这说明数据库、HDFS、Hive、Spark、Python 基础环境都可以连通。

## 2. 终端说明

你当前常用终端可以这样分工：

```text
pwsh    Windows 主机终端
mysql   MySQL 客户端终端
python  Python 容器终端
hadoop  Hadoop NameNode 终端
hive    Hive / Beeline 终端
spark   Spark Master 终端
redis   Redis 终端
```

后续命令按终端执行，避免把 Hive 输出粘到 bash 里。

## 3. MySQL 准备数据

在 `mysql` 终端进入数据库：

```sql
USE zhitu;
```

如果中文显示异常，执行：

```sql
SET NAMES utf8mb4;
```

创建原始招聘表：

```sql
CREATE TABLE IF NOT EXISTS raw_jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_title VARCHAR(100) NOT NULL,
    company_name VARCHAR(150) NOT NULL,
    city VARCHAR(50) NOT NULL,
    district VARCHAR(50),
    salary_text VARCHAR(50) NOT NULL,
    salary_min DECIMAL(10, 2),
    salary_max DECIMAL(10, 2),
    education VARCHAR(50),
    experience VARCHAR(50),
    skills VARCHAR(255),
    industry VARCHAR(100),
    source VARCHAR(50) DEFAULT 'mock',
    source_url VARCHAR(255),
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

插入 3 条模拟数据：

```sql
INSERT INTO raw_jobs (
    job_title, company_name, city, district, salary_text,
    salary_min, salary_max, education, experience, skills,
    industry, source, source_url
) VALUES
('大数据开发实习生', '上海云舟科技有限公司', '上海', '浦东新区', '8-12K', 8.00, 12.00, '本科', '在校/应届', 'Python,Spark,Hive,SQL', '互联网', 'mock', 'mock://job/001'),
('数据分析师', '杭州数智信息技术有限公司', '杭州', '西湖区', '10-15K', 10.00, 15.00, '本科', '1-3年', 'Python,Pandas,MySQL,ECharts', '数据服务', 'mock', 'mock://job/002'),
('数据仓库工程师', '北京星河数据有限公司', '北京', '海淀区', '15-25K', 15.00, 25.00, '本科', '3-5年', 'Hive,Spark,ETL,Hadoop', '软件服务', 'mock', 'mock://job/003');
```

创建清洗表：

```sql
DROP TABLE IF EXISTS clean_jobs;

CREATE TABLE clean_jobs AS
SELECT
    id AS raw_id,
    job_title,
    company_name,
    city,
    district,
    salary_text,
    salary_min,
    salary_max,
    ROUND((salary_min + salary_max) / 2, 2) AS salary_avg,
    education,
    experience,
    skills,
    industry,
    source_url,
    crawled_at
FROM raw_jobs
WHERE job_title IS NOT NULL
  AND company_name IS NOT NULL
  AND city IS NOT NULL;
```

查看数据：

```sql
SELECT raw_id, job_title, company_name, city, salary_text, salary_avg, skills
FROM clean_jobs;
```

MySQL 里直接分析：

```sql
SELECT
    city,
    COUNT(*) AS job_count,
    ROUND(AVG(salary_avg), 2) AS avg_salary
FROM clean_jobs
GROUP BY city
ORDER BY avg_salary DESC;
```

## 4. 导出 MySQL 数据到文件

在 `pwsh` 终端执行：

```powershell
cd D:\bigdatashixun\project
mkdir data
```

导出 `clean_jobs`：

```powershell
mysql --default-character-set=utf8mb4 --batch --raw --skip-column-names -h127.0.0.1 -P13306 -uzhitu -pzhitu123456 zhitu -e "SELECT raw_id, job_title, company_name, city, salary_text, salary_avg, education, experience, skills FROM clean_jobs;" > data\clean_jobs.tsv
```

查看文件：

```powershell
Get-Content data\clean_jobs.tsv
```

如果 `pwsh` 里没有 `mysql` 命令，也可以在 MySQL 容器中导出，或者先用你已经打通的 Python 脚本生成文件。

## 5. 上传到 HDFS

如果 `hadoop` 终端不能直接访问 `D:\bigdatashixun\project\data`，先在 `pwsh` 里复制到 NameNode 容器：

```powershell
docker cp data\clean_jobs.tsv zhitu-hadoop-namenode:/tmp/clean_jobs.tsv
```

在 `hadoop` 终端检查文件：

```bash
ls -l /tmp/clean_jobs.tsv
```

创建 HDFS 目录：

```bash
hdfs dfs -mkdir -p /user/zhitu/jobs
```

上传文件：

```bash
hdfs dfs -put -f /tmp/clean_jobs.tsv /user/zhitu/jobs/clean_jobs.tsv
```

查看 HDFS 文件：

```bash
hdfs dfs -ls /user/zhitu/jobs
hdfs dfs -cat /user/zhitu/jobs/clean_jobs.tsv
```

到这里说明：

```text
MySQL -> TSV -> HDFS
```

已经打通。

## 6. Hive 读取 HDFS 数据

在 `hive` 终端进入 Beeline：

```bash
beeline -u jdbc:hive2://hiveserver2:10000
```

创建并使用数据库：

```sql
CREATE DATABASE IF NOT EXISTS zhitu;
USE zhitu;
```

创建 Hive 外部表：

```sql
DROP TABLE IF EXISTS clean_jobs_hive;

CREATE EXTERNAL TABLE clean_jobs_hive (
    raw_id BIGINT,
    job_title STRING,
    company_name STRING,
    city STRING,
    salary_text STRING,
    salary_avg DOUBLE,
    education STRING,
    experience STRING,
    skills STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/user/zhitu/jobs';
```

查询数据：

```sql
SELECT * FROM clean_jobs_hive;
```

如果执行 `GROUP BY` 报 `Could not find or load main class org.apache.hadoop.mapreduce.v2.app.MRAppMaster`，先在 Beeline 里执行：

```sql
SET yarn.app.mapreduce.am.env=HADOOP_MAPRED_HOME=/opt/hadoop-3.3.6;
SET mapreduce.map.env=HADOOP_MAPRED_HOME=/opt/hadoop-3.3.6;
SET mapreduce.reduce.env=HADOOP_MAPRED_HOME=/opt/hadoop-3.3.6;
```

再执行 Hive 分析：

```sql
SELECT
    city,
    COUNT(*) AS job_count,
    ROUND(AVG(salary_avg), 2) AS avg_salary
FROM clean_jobs_hive
GROUP BY city
ORDER BY avg_salary DESC;
```

注意：Hive 第一次查询慢是正常的。`GROUP BY` 会启动 MapReduce，哪怕只有 3 行数据，也可能需要几十秒。

## 7. Spark 直接读取 MySQL

Spark 读取 MySQL 需要 MySQL JDBC 驱动。

在 `pwsh` 终端复制驱动到 Spark Master：

```powershell
cd D:\bigdatashixun\project
docker cp docker\build-context\assets\mysql-connector-j-8.0.33.jar zhitu-spark-master:/opt/spark/jars/mysql-connector-j-8.0.33.jar
```

如果 Spark Worker 也需要驱动，复制到 Worker：

```powershell
docker cp docker\build-context\assets\mysql-connector-j-8.0.33.jar zhitu-spark-worker:/opt/spark/jars/mysql-connector-j-8.0.33.jar
```

在 `spark` 终端检查：

```bash
ls -l /opt/spark/jars/mysql-connector-j-8.0.33.jar
```

如果 Spark 任务一直显示：

```text
Initial job has not accepted any resources
```

说明 Spark 资源被旧的 `pyspark` 或 `spark-sql` 会话占用。关闭旧会话，或者在 `pwsh` 终端重启 Spark：

```powershell
docker compose restart spark-master spark-worker
```

## 8. Python 脚本读取 MySQL 并用 Spark 分析

在 `python` 终端检查 PySpark：

```bash
python -c "import pyspark; print(pyspark.__version__)"
```

运行本项目的最小贯通脚本：

```bash
cd /workspace/src/python
python mysql_spark_end_to_end_demo.py
```

该脚本会完成：

```text
创建 MySQL demo_raw_jobs
插入 3 条模拟数据
创建 MySQL demo_clean_jobs
Spark JDBC 读取 demo_clean_jobs
Spark 计算城市平均薪资
分析结果写回 MySQL demo_city_salary_spark
分析结果写入 HDFS /user/zhitu/demo/city_salary_spark
```

## 9. 常见问题

### 中文显示为问号

MySQL 里执行：

```sql
SET NAMES utf8mb4;
```

PowerShell 里执行：

```powershell
chcp 65001
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

连接 MySQL 时带上：

```bash
--default-character-set=utf8mb4
```

### Hive SELECT 快，但 GROUP BY 慢

`SELECT *` 可以直接读取 HDFS 文件。`GROUP BY` 会启动 MapReduce，所以慢很多。

### yarn logs 找不到日志

当前环境没有开启 YARN 日志聚合，所以 `yarn logs` 找不到日志是正常现象。可以看 ResourceManager / NodeManager 容器日志。

### Spark 一直等待资源

检查 Spark UI 或重启 Spark：

```powershell
docker compose restart spark-master spark-worker
```

## 10. 删除本次演示数据的命令

以下命令只删除本次演示用的数据表、Hive 表和 HDFS 文件，不删除 Docker 镜像和容器数据卷。

### 删除 MySQL 数据表

在 `mysql` 终端执行：

```sql
USE zhitu;

DROP TABLE IF EXISTS analysis_city_salary;
DROP TABLE IF EXISTS analysis_job_salary;
DROP TABLE IF EXISTS analysis_city_salary_spark;
DROP TABLE IF EXISTS demo_city_salary_spark;
DROP TABLE IF EXISTS demo_clean_jobs;
DROP TABLE IF EXISTS demo_raw_jobs;
DROP TABLE IF EXISTS clean_jobs;
DROP TABLE IF EXISTS raw_jobs;

SHOW TABLES;
```

### 删除 Hive 表

在 `hive` 终端执行：

```sql
USE zhitu;

DROP TABLE IF EXISTS clean_jobs_hive;

SHOW TABLES;
```

如果想连 Hive 数据库也删除：

```sql
DROP DATABASE IF EXISTS zhitu CASCADE;
```

### 删除 HDFS 文件

在 `hadoop` 终端执行：

```bash
hdfs dfs -rm -f /user/zhitu/jobs/clean_jobs.tsv
hdfs dfs -rm -r -f /user/zhitu/jobs
hdfs dfs -rm -r -f /user/zhitu/demo
hdfs dfs -ls /user/zhitu
```

### 删除 Windows 本地导出文件

在 `pwsh` 终端执行：

```powershell
cd D:\bigdatashixun\project
Remove-Item -Force data\clean_jobs.tsv
```

如果 `data` 目录已经空了，可以删除目录：

```powershell
Remove-Item -Force data
```

## 11. 最小贯通 Python 代码

完整代码已经放在：

```text
src/python/mysql_spark_end_to_end_demo.py
```

运行命令：

```bash
cd /workspace/src/python
python mysql_spark_end_to_end_demo.py
```

这段代码适合做项目答辩时的“最小可运行流程”演示。
