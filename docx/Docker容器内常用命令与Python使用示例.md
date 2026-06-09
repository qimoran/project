# Docker 容器内常用命令与 Python 使用示例

本文档记录进入 Docker 大数据环境后，MySQL、Redis、Hadoop/HDFS、Hive、Spark 的常用命令，以及在 Python 容器中访问这些服务的代码示例。

默认从项目根目录执行宿主机命令：

```powershell
cd D:\bigdatashixun\project
```

确认环境已启动：

```powershell
.\scripts\bigdata-docker.cmd status
```

## 1. 容器和地址速查

| 服务 | 进入容器 | 容器内地址 | 宿主机地址 |
| --- | --- | --- | --- |
| MySQL | `docker compose exec mysql bash` | `mysql:3306` | `127.0.0.1:13306` |
| Redis | `docker compose exec redis sh` | `redis:6379` | `127.0.0.1:16379` |
| Hadoop NameNode | `docker compose exec namenode bash` | `namenode:9000` / `namenode:9870` | `127.0.0.1:9000` / `127.0.0.1:9870` |
| YARN ResourceManager | `docker compose exec resourcemanager bash` | `resourcemanager:8088` | `127.0.0.1:8088` |
| HiveServer2 | `docker compose exec hiveserver2 bash` | `hiveserver2:10000` / `hiveserver2:10002` | `127.0.0.1:10000` / `127.0.0.1:10002` |
| Spark Master | `docker compose exec spark-master bash` | `spark://spark-master:7077` / `spark-master:8080` | `127.0.0.1:7077` / `127.0.0.1:18080` |
| Python 工具容器 | `docker compose exec python bash` | `/workspace` | 无需端口 |

Python 代码推荐写在：

```text
D:\bigdatashixun\project\src\python
```

在 Python 容器中运行：

```powershell
docker compose exec -T python python src/python/your_script.py
```

## 2. MySQL 常用命令

### 2.1 直接进入 MySQL 命令行

```powershell
docker compose exec mysql mysql -uroot -proot123456
```

进入后常用 SQL：

```sql
show databases;
use zhitu;
show tables;
select database();
select version();
```

创建测试库和测试表：

```sql
create database if not exists demo_db default character set utf8mb4;
use demo_db;

create table if not exists students (
  id int primary key auto_increment,
  name varchar(50) not null,
  score int not null,
  created_at timestamp default current_timestamp
);

insert into students (name, score) values ('alice', 95), ('bob', 88);
select * from students;
```

查看表结构：

```sql
desc students;
show create table students\G
```

删除测试数据：

```sql
delete from students where name = 'alice';
drop table if exists students;
drop database if exists demo_db;
```

退出：

```sql
exit;
```

### 2.2 不进入交互界面直接执行

```powershell
docker compose exec -T mysql mysql -uroot -proot123456 -e "show databases;"
docker compose exec -T mysql mysql -uroot -proot123456 -D zhitu -e "show tables;"
```

## 3. Redis 常用命令

### 3.1 进入 Redis CLI

```powershell
docker compose exec redis redis-cli
```

进入后检查连接：

```redis
PING
INFO server
DBSIZE
```

字符串：

```redis
SET demo:name alice
GET demo:name
EXISTS demo:name
DEL demo:name
```

过期时间：

```redis
SET demo:code 123456
EXPIRE demo:code 60
TTL demo:code
GET demo:code
```

Hash：

```redis
HSET demo:user:1 name alice score 95
HGETALL demo:user:1
HGET demo:user:1 name
HDEL demo:user:1 score
```

List：

```redis
LPUSH demo:list a b c
LRANGE demo:list 0 -1
RPOP demo:list
```

Set：

```redis
SADD demo:set mysql redis spark
SMEMBERS demo:set
SISMEMBER demo:set spark
```

Key 扫描：

```redis
SCAN 0 MATCH demo:* COUNT 20
```

小数据测试时可以用：

```redis
KEYS demo:*
```

谨慎使用清空命令：

```redis
FLUSHDB
FLUSHALL
```

### 3.2 不进入交互界面直接执行

```powershell
docker compose exec -T redis redis-cli PING
docker compose exec -T redis redis-cli SET demo:name alice
docker compose exec -T redis redis-cli GET demo:name
```

## 4. Hadoop / HDFS 常用命令

HDFS 命令主要在 NameNode 容器中执行：

```powershell
docker compose exec namenode bash
```

### 4.1 查看 HDFS

```bash
hdfs dfs -ls /
hdfs dfs -ls /user
hdfs dfs -df -h /
hdfs dfsadmin -report
```

### 4.2 创建目录、上传、查看、下载

在容器里创建一个本地测试文件：

```bash
printf "hello hdfs\nhello docker\n" > /tmp/demo.txt
```

上传到 HDFS：

```bash
hdfs dfs -mkdir -p /user/root/input
hdfs dfs -put -f /tmp/demo.txt /user/root/input/demo.txt
hdfs dfs -ls /user/root/input
```

查看文件内容：

```bash
hdfs dfs -cat /user/root/input/demo.txt
hdfs dfs -text /user/root/input/demo.txt
```

下载回容器本地：

```bash
hdfs dfs -get -f /user/root/input/demo.txt /tmp/demo-from-hdfs.txt
cat /tmp/demo-from-hdfs.txt
```

### 4.3 文件管理

```bash
hdfs dfs -du -h /user/root/input
hdfs dfs -count /user/root/input
hdfs dfs -mv /user/root/input/demo.txt /user/root/input/demo2.txt
hdfs dfs -cp /user/root/input/demo2.txt /user/root/input/demo-copy.txt
hdfs dfs -rm /user/root/input/demo-copy.txt
hdfs dfs -rm -r /user/root/input
```

### 4.4 权限

```bash
hdfs dfs -chmod 755 /user/root
hdfs dfs -chown root:supergroup /user/root
```

### 4.5 YARN 检查

在 ResourceManager 容器或任意 Hadoop 容器中执行：

```powershell
docker compose exec resourcemanager bash
```

```bash
yarn node -list
yarn application -list
```

## 5. Hive 常用命令

Hive 推荐通过 HiveServer2 的 Beeline 执行：

```powershell
docker compose exec hiveserver2 beeline -u "jdbc:hive2://localhost:10000" -n root
```

### 5.1 基础 SQL

进入 Beeline 后：

```sql
show databases;
create database if not exists demo_hive;
use demo_hive;
show tables;
```

创建内部表：

```sql
create table if not exists students (
  id int,
  name string,
  score int
)
stored as parquet;
```

插入和查询：

```sql
insert into students values (1, 'alice', 95), (2, 'bob', 88);
select * from students;
select count(*) from students;
```

查看表结构：

```sql
desc students;
desc formatted students;
show create table students;
```

删除测试对象：

```sql
drop table if exists students;
drop database if exists demo_hive cascade;
```

退出：

```sql
!quit
```

### 5.2 不进入交互界面直接执行

```powershell
docker compose exec -T hiveserver2 beeline -u "jdbc:hive2://localhost:10000" -n root -e "show databases;"
docker compose exec -T hiveserver2 beeline -u "jdbc:hive2://localhost:10000" -n root -e "create database if not exists demo_hive;"
```

### 5.3 Hive 外部表示例

先在 NameNode 容器里准备 HDFS 数据：

```powershell
docker compose exec namenode bash
```

```bash
mkdir -p /tmp/hive-demo
cat > /tmp/hive-demo/students.csv <<'EOF'
1,alice,95
2,bob,88
EOF

hdfs dfs -mkdir -p /user/root/hive-demo/students
hdfs dfs -put -f /tmp/hive-demo/students.csv /user/root/hive-demo/students/
```

再进入 Beeline：

```powershell
docker compose exec hiveserver2 beeline -u "jdbc:hive2://localhost:10000" -n root
```

```sql
create database if not exists demo_hive;
use demo_hive;

drop table if exists ext_students;

create external table ext_students (
  id int,
  name string,
  score int
)
row format delimited
fields terminated by ','
stored as textfile
location '/user/root/hive-demo/students';

select * from ext_students;
```

## 6. Spark 常用命令

Spark Master 地址：

```text
spark://spark-master:7077
```

### 6.1 Spark SQL

直接执行一条 SQL：

```powershell
docker compose exec -T spark-master spark-sql --master spark://spark-master:7077 -e "show databases;"
```

进入 Spark SQL 交互界面：

```powershell
docker compose exec spark-master spark-sql --master spark://spark-master:7077
```

常用 SQL：

```sql
show databases;
create database if not exists demo_spark;
use demo_spark;
show tables;
select current_database();
```

创建表并查询：

```sql
create table if not exists students (id int, name string, score int) using parquet;
insert into students values (1, 'alice', 95), (2, 'bob', 88);
select * from students;
```

退出：

```sql
exit;
```

### 6.2 PySpark 交互界面

进入 PySpark：

```powershell
docker compose exec spark-master pyspark --master spark://spark-master:7077 --conf spark.sql.catalogImplementation=hive
```

进入后执行：

```python
spark.sql("show databases").show()
df = spark.range(1, 6)
df.show()
df.count()
```

读取和写入 HDFS：

```python
data = [(1, "alice", 95), (2, "bob", 88)]
df = spark.createDataFrame(data, ["id", "name", "score"])
df.write.mode("overwrite").parquet("hdfs://namenode:9000/user/root/spark-demo/students")

spark.read.parquet("hdfs://namenode:9000/user/root/spark-demo/students").show()
```

退出：

```python
exit()
```

## 7. Python 中使用 MySQL

把代码保存为：

```text
src/python/demo_mysql.py
```

代码：

```python
import pymysql


conn = pymysql.connect(
    host="mysql",
    port=3306,
    user="root",
    password="root123456",
    database="zhitu",
    charset="utf8mb4",
    autocommit=True,
)

try:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            create table if not exists demo_students (
              id int primary key auto_increment,
              name varchar(50) not null,
              score int not null
            )
            """
        )
        cursor.execute(
            "insert into demo_students (name, score) values (%s, %s)",
            ("alice", 95),
        )
        cursor.execute("select id, name, score from demo_students order by id desc limit 5")
        for row in cursor.fetchall():
            print(row)
finally:
    conn.close()
```

运行：

```powershell
docker compose exec -T python python src/python/demo_mysql.py
```

## 8. Python 中使用 Redis

把代码保存为：

```text
src/python/demo_redis.py
```

代码：

```python
import redis


r = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True,
    protocol=2,
)

print("PING:", r.ping())

r.set("demo:name", "alice")
print("demo:name =", r.get("demo:name"))

r.hset("demo:user:1", mapping={"name": "alice", "score": "95"})
print("demo:user:1 =", r.hgetall("demo:user:1"))

r.lpush("demo:list", "a", "b", "c")
print("demo:list =", r.lrange("demo:list", 0, -1))

r.expire("demo:name", 60)
print("ttl demo:name =", r.ttl("demo:name"))
```

运行：

```powershell
docker compose exec -T python python src/python/demo_redis.py
```

说明：当前 Redis 是 5.0.14，Python 代码中固定 `protocol=2`，避免 RESP3 的 `HELLO 3` 兼容问题。

## 9. Python 中使用 HDFS

当前 Python 容器没有额外安装 HDFS 客户端库，推荐直接使用 WebHDFS HTTP API。把代码保存为：

```text
src/python/demo_hdfs_webhdfs.py
```

代码：

```python
import requests


BASE_URL = "http://namenode:9870/webhdfs/v1"
USER = "root"


def webhdfs_url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return BASE_URL + path


def list_status(path: str) -> None:
    response = requests.get(
        webhdfs_url(path),
        params={"op": "LISTSTATUS", "user.name": USER},
        timeout=10,
    )
    response.raise_for_status()
    items = response.json()["FileStatuses"]["FileStatus"]
    print("LIST", path)
    for item in items:
        print(item["type"], item["pathSuffix"], item.get("length", 0))


def mkdirs(path: str) -> None:
    response = requests.put(
        webhdfs_url(path),
        params={"op": "MKDIRS", "user.name": USER},
        timeout=10,
    )
    response.raise_for_status()
    print("MKDIRS", path, response.json())


def create_file(path: str, content: str) -> None:
    response = requests.put(
        webhdfs_url(path),
        params={"op": "CREATE", "overwrite": "true", "user.name": USER},
        allow_redirects=False,
        timeout=10,
    )
    response.raise_for_status()
    upload_url = response.headers["Location"]

    upload = requests.put(upload_url, data=content.encode("utf-8"), timeout=10)
    upload.raise_for_status()
    print("CREATE", path)


def read_file(path: str) -> str:
    response = requests.get(
        webhdfs_url(path),
        params={"op": "OPEN", "user.name": USER},
        timeout=10,
    )
    response.raise_for_status()
    return response.text


mkdirs("/user/root/python-demo")
create_file("/user/root/python-demo/hello.txt", "hello hdfs from python\n")
list_status("/user/root/python-demo")
print(read_file("/user/root/python-demo/hello.txt"))
```

运行：

```powershell
docker compose exec -T python python src/python/demo_hdfs_webhdfs.py
```

## 10. Python 中使用 Spark

把代码保存为：

```text
src/python/demo_spark.py
```

代码：

```python
from pyspark.sql import SparkSession


spark = (
    SparkSession.builder
    .master("spark://spark-master:7077")
    .appName("demo-spark-python")
    .getOrCreate()
)

try:
    df = spark.createDataFrame(
        [(1, "alice", 95), (2, "bob", 88), (3, "cindy", 92)],
        ["id", "name", "score"],
    )

    df.show()
    df.createOrReplaceTempView("students")

    spark.sql(
        """
        select
          count(*) as student_count,
          avg(score) as avg_score
        from students
        """
    ).show()

    output_path = "hdfs://namenode:9000/user/root/spark-python-demo/students"
    df.write.mode("overwrite").parquet(output_path)

    loaded = spark.read.parquet(output_path)
    loaded.show()
finally:
    spark.stop()
```

运行：

```powershell
docker compose exec -T python python src/python/demo_spark.py
```

## 11. Python 中使用 Spark + Hive

当前 Python 容器没有单独安装 PyHive。访问 Hive 推荐使用 PySpark 开启 Hive 支持，通过 Hive Metastore 操作库表。

把代码保存为：

```text
src/python/demo_spark_hive.py
```

代码：

```python
from pyspark.sql import SparkSession


spark = (
    SparkSession.builder
    .master("spark://spark-master:7077")
    .appName("demo-spark-hive-python")
    .config("spark.sql.catalogImplementation", "hive")
    .config("spark.hadoop.hive.metastore.uris", "thrift://hive-metastore:9083")
    .config("spark.sql.warehouse.dir", "hdfs://namenode:9000/user/hive/warehouse")
    .enableHiveSupport()
    .getOrCreate()
)

try:
    spark.sql("show databases").show(truncate=False)

    spark.sql("create database if not exists demo_python_hive")
    spark.sql("use demo_python_hive")
    spark.sql("drop table if exists students")
    spark.sql("create table students (id int, name string, score int)")
    spark.sql("insert into students values (1, 'alice', 95), (2, 'bob', 88)")

    spark.sql("show tables").show(truncate=False)
    spark.sql("select * from students").show()
finally:
    spark.stop()
```

运行：

```powershell
docker compose exec -T python python src/python/demo_spark_hive.py
```

如果只想快速确认 Spark 能访问 Hive，也可以直接运行：

```powershell
docker compose exec -T spark-master spark-sql --master spark://spark-master:7077 -e "show databases;"
```

## 12. 一个综合检查脚本

项目已有总检查脚本：

```text
src/python/check_bigdata_connections.py
```

基础检查：

```powershell
docker compose exec -T python python src/python/check_bigdata_connections.py
```

包含 Spark 小任务：

```powershell
docker compose exec -T python python src/python/check_bigdata_connections.py --spark-job
```

期望结果：

```text
Result: 14/14 checks passed
Result: 15/15 checks passed
```

## 13. 常用原则

- 在 Windows 宿主机访问服务时，使用 `127.0.0.1` 和映射端口，例如 MySQL `13306`、Redis `16379`。
- 在 Docker 容器内部访问服务时，使用 Compose 服务名和容器端口，例如 `mysql:3306`、`redis:6379`、`namenode:9000`。
- Python 代码优先在 `zhitu-python` 容器中运行，不优先使用 Windows 本机 Python。
- HDFS 文件路径使用 `hdfs://namenode:9000/...` 或 WebHDFS `http://namenode:9870/webhdfs/v1/...`。
- Hive 交互命令优先用 Beeline，Python 代码里优先用 Spark SQL 访问 Hive Metastore。
- `drop database`、`drop table`、`hdfs dfs -rm -r`、`FLUSHDB`、`FLUSHALL` 都是删除命令，真实数据上谨慎使用。
