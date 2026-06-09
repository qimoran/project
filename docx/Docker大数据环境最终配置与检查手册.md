# Docker 大数据环境最终配置与检查手册

本文档是当前 Docker 大数据环境的最终优先参考手册。以后启动、停止、写代码、检查连通性、排查常见问题时，优先看这一份。

旧文档 `Docker大数据环境执行文档.md` 和 `Docker下载与验证说明.md` 保留作为过程记录，不再作为第一操作依据。本手册以当前已经跑通的 Docker Desktop + WSL2 + Docker Compose 环境为准，不再讲原生 Windows 手动安装 Hadoop、Hive、Spark 的完整流程。

## 1. 环境总览

当前环境由 Docker Desktop + WSL2 + Docker Compose 管理，项目根目录是：

```text
D:\bigdatashixun\project
```

Docker Desktop 程序本体可能仍安装在 C 盘，这是正常的。真正占空间的 Docker WSL 数据目录已经通过 Junction 指向 D 盘：

```text
%LOCALAPPDATA%\Docker\wsl  ->  D:\docker\desktop-wsl
```

业务持久化数据单独放在：

```text
D:\docker\bigdata\data
```

结论：

- `D:\docker\desktop-wsl`：Docker Desktop / WSL 的重数据位置。
- `D:\docker\bigdata\data`：MySQL、Redis、HDFS、Spark 等服务的业务持久化数据。
- `D:\bigdatashixun\project`：项目代码、脚本、Docker Compose 配置和文档。

不要把业务代码写到 `D:\docker\bigdata\data`。这个目录只给容器保存数据。

## 2. 目录说明

| 路径 | 用途 |
| --- | --- |
| `D:\bigdatashixun\project` | 项目根目录，执行 Docker Compose 命令的位置 |
| `D:\bigdatashixun\project\src\python` | Python 代码目录，推荐把连接检查、爬虫、数据处理脚本放这里 |
| `D:\bigdatashixun\project\src\spark` | Spark 作业代码目录 |
| `D:\bigdatashixun\project\src\sql` | SQL 文件目录 |
| `D:\bigdatashixun\project\scripts` | 启动、停止、检查、准备环境的脚本目录 |
| `D:\bigdatashixun\project\docker` | Docker 构建上下文、配置文件、初始化脚本 |
| `D:\docker\bigdata\data` | Docker 大数据服务持久化数据目录，不放代码 |
| `D:\docker\desktop-wsl` | Docker Desktop WSL 重数据目录 |

当前 Python 总检查脚本是：

```text
D:\bigdatashixun\project\src\python\check_bigdata_connections.py
```

## 3. 服务清单

| 服务 | Compose 服务名 | 容器名 | 宿主机端口 | 容器内地址 |
| --- | --- | --- | --- | --- |
| MySQL | `mysql` | `zhitu-mysql` | `13306` | `mysql:3306` |
| Redis | `redis` | `zhitu-redis` | `16379` | `redis:6379` |
| HDFS NameNode RPC | `namenode` | `zhitu-hadoop-namenode` | `9000` | `namenode:9000` |
| HDFS NameNode Web UI | `namenode` | `zhitu-hadoop-namenode` | `9870` | `namenode:9870` |
| YARN ResourceManager UI | `resourcemanager` | `zhitu-yarn-resourcemanager` | `8088` | `resourcemanager:8088` |
| Hive Metastore | `hive-metastore` | `zhitu-hive-metastore` | `9083` | `hive-metastore:9083` |
| HiveServer2 JDBC | `hiveserver2` | `zhitu-hiveserver2` | `10000` | `hiveserver2:10000` |
| HiveServer2 Web UI | `hiveserver2` | `zhitu-hiveserver2` | `10002` | `hiveserver2:10002` |
| Spark Master | `spark-master` | `zhitu-spark-master` | `7077` | `spark://spark-master:7077` |
| Spark Master Web UI | `spark-master` | `zhitu-spark-master` | `18080` | `spark-master:8080` |
| Spark Worker Web UI | `spark-worker` | `zhitu-spark-worker` | `18081` | `spark-worker:8081` |
| Python 工具容器 | `python` | `zhitu-python` | 无需映射 | 工作目录 `/workspace` |

常用 Web 页面：

```text
HDFS NameNode: http://localhost:9870
YARN:          http://localhost:8088
HiveServer2:   http://localhost:10002
Spark Master:  http://localhost:18080
Spark Worker:  http://localhost:18081
```

## 4. 启动与停止

所有命令都建议在 PowerShell 中从项目根目录执行：

```powershell
cd D:\bigdatashixun\project
```

启动完整大数据环境：

```powershell
.\scripts\bigdata-docker.cmd up-all
```

查看容器状态：

```powershell
.\scripts\bigdata-docker.cmd status
```

查看日志：

```powershell
.\scripts\bigdata-docker.cmd logs
```

`logs` 会持续跟随输出。看完后按 `Ctrl+C` 回到命令行。

停止环境：

```powershell
.\scripts\bigdata-docker.cmd down
```

`down` 会停止并删除容器，但不会删除 `D:\docker\bigdata\data` 中的持久化数据。

如果只是临时重启服务：

```powershell
.\scripts\bigdata-docker.cmd restart
```

如果修改了 Dockerfile 或镜像构建内容，再手动构建：

```powershell
.\scripts\bigdata-docker.cmd build
```

当前 `up-all` 使用 `--no-build`，已构建镜像存在时不会反复强制构建。

## 5. 写代码位置

推荐规则：

- Python 代码写到 `src\python`。
- Spark 代码写到 `src\spark`。
- SQL 文件写到 `src\sql`。
- 容器持久化数据自动写到 `D:\docker\bigdata\data`，不要手工把代码放进去。

示例：

```text
D:\bigdatashixun\project\src\python\check_bigdata_connections.py
D:\bigdatashixun\project\src\spark\your_spark_job.py
D:\bigdatashixun\project\src\sql\your_query.sql
```

Python 容器把项目根目录挂载为 `/workspace`，所以容器内看到的路径是：

```text
/workspace/src/python
/workspace/src/spark
/workspace/src/sql
```

## 6. Python 容器使用

进入 Python 工具容器：

```powershell
docker compose exec python bash
```

进入容器后运行检查脚本：

```bash
python src/python/check_bigdata_connections.py
```

不进入容器，直接从 Windows 终端调用容器里的 Python：

```powershell
docker compose exec -T python python src/python/check_bigdata_connections.py
```

运行包含 Spark 小任务的检查：

```powershell
docker compose exec -T python python src/python/check_bigdata_connections.py --spark-job
```

不要优先使用 Windows 本机 Python 直接运行：

```powershell
python .\src\python\check_bigdata_connections.py
```

原因是 Windows 本机 Python 可能没有安装 `pymysql`、`redis`、`requests`、`pyspark` 等包，并且本机访问容器网络名 `mysql`、`redis`、`namenode` 也不如容器内稳定。项目依赖已经放在 Python 工具容器 `zhitu-python` 里，优先用容器运行。

也可以使用封装脚本进入 Python 容器：

```powershell
.\scripts\bigdata-docker.cmd python
```

## 7. 连通性检查

### 7.1 容器状态

```powershell
.\scripts\bigdata-docker.cmd status
```

正常情况下应看到 MySQL、Redis、Hadoop、Hive、Spark、Python 相关容器处于 `running` 或健康状态。

### 7.2 宿主机端口检查

```powershell
Test-NetConnection 127.0.0.1 -Port 13306
Test-NetConnection 127.0.0.1 -Port 16379
Test-NetConnection 127.0.0.1 -Port 9870
Test-NetConnection 127.0.0.1 -Port 8088
Test-NetConnection 127.0.0.1 -Port 10000
Test-NetConnection 127.0.0.1 -Port 18080
```

`TcpTestSucceeded : True` 表示端口可达。

### 7.3 MySQL 查询

```powershell
docker compose exec -T mysql mysql -uroot -proot123456 -e "show databases;"
```

应能看到 `zhitu`、`hive_metastore` 等数据库。

### 7.4 Redis PING

```powershell
docker compose exec -T redis redis-cli ping
```

应返回：

```text
PONG
```

### 7.5 HDFS 检查

```powershell
docker compose exec -T namenode hdfs dfs -ls /
```

如能列出 HDFS 根目录，说明 NameNode 和 HDFS 命令可用。

### 7.6 Hive Beeline 检查

```powershell
docker compose exec -T hiveserver2 beeline -u "jdbc:hive2://localhost:10000" -n root -e "show databases;"
```

应能看到 `default` 以及已经创建过的 Hive 数据库。

也可以进入交互式 Beeline：

```powershell
.\scripts\bigdata-docker.cmd beeline
```

### 7.7 Spark SQL 检查

```powershell
docker compose exec -T spark-master spark-sql --master spark://spark-master:7077 -e "show databases;"
```

Spark SQL 能返回数据库列表，说明 Spark 能通过 Hive 配置访问 Metastore。

### 7.8 Python 总检查脚本

基础检查：

```powershell
docker compose exec -T python python src/python/check_bigdata_connections.py
```

期望结果：

```text
Result: 14/14 checks passed
```

包含 Spark 小任务检查：

```powershell
docker compose exec -T python python src/python/check_bigdata_connections.py --spark-job
```

期望结果：

```text
Result: 15/15 checks passed
```

## 8. Spark + Hive 检查

### 8.1 Spark SQL 直接检查

```powershell
docker compose exec -T spark-master spark-sql --master spark://spark-master:7077 -e "show databases;"
```

如果返回数据库列表，说明 Spark SQL 已经能读取 Hive Metastore。

### 8.2 进入 PySpark

```powershell
docker compose exec spark-master pyspark --master spark://spark-master:7077 --conf spark.sql.catalogImplementation=hive
```

进入 PySpark 后执行：

```python
spark.sql("show databases").show()
spark.sql("create database if not exists test_spark_hive")
spark.sql("show tables").show()
```

如果 `show databases` 能显示 `default` 和 `test_spark_hive`，说明 Spark + Hive 联通正常。

如需清理测试库：

```python
spark.sql("drop database if exists test_spark_hive cascade")
```

退出 PySpark：

```python
exit()
```

## 9. 常见报错处理

### 9.1 `auth.docker.io/token EOF`

这是 Docker Hub 网络问题，通常不是 Compose 配置错误。

处理方式：

1. 如果镜像已经构建完成，直接运行：

   ```powershell
   .\scripts\bigdata-docker.cmd up-all
   ```

   当前 `up-all` 不再强制 build。

2. 如果确实缺镜像，稍后重试：

   ```powershell
   .\scripts\bigdata-docker.cmd build
   ```

### 9.2 `apt-get 502 Bad Gateway`

多数是代理导致 Debian/Ubuntu 源访问异常。当前建议 `.env` 中保持：

```env
HTTP_PROXY=
HTTPS_PROXY=
```

如果直连不通，再按实际代理恢复为：

```env
HTTP_PROXY=http://host.docker.internal:7897
HTTPS_PROXY=http://host.docker.internal:7897
```

改完 `.env` 后，如需重新构建镜像再运行：

```powershell
.\scripts\bigdata-docker.cmd build
```

### 9.3 Windows 本机 Python 缺包

如果看到类似：

```text
ModuleNotFoundError: No module named 'pymysql'
```

不要优先在 Windows 本机补包。直接用 Docker Python 容器运行：

```powershell
docker compose exec -T python python src/python/check_bigdata_connections.py
```

### 9.4 Redis `HELLO 3` 报错

当前 Redis 版本是 5.0.14，使用 RESP2 协议。检查脚本已经固定：

```python
redis.Redis(..., protocol=2)
```

如果以后改脚本，不要改回默认 RESP3。

### 9.5 HiveServer2 启动或权限问题

当前 Hive 配置已经包含：

```xml
<name>hive.metastore.event.db.notification.api.auth</name>
<value>false</value>

<name>hive.server2.enable.doAs</name>
<value>false</value>
```

这两个配置用于避免本地实训环境里的 Metastore 事件权限和用户代理权限问题。不要随意删掉。

### 9.6 Java 版本问题

当前大数据容器使用 Java 8：

- Hadoop 容器：Java 8
- Hive 容器：Java 8
- Spark 容器：Java 8

Python 工具容器和 Windows 本机可以是 Java 21，不影响大数据容器运行。

如果课程或依赖要求 Java 11，需要修改对应 Dockerfile 的基础镜像并重新构建：

```powershell
.\scripts\bigdata-docker.cmd build
```

不要只改 Windows 本机 Java 版本来期待容器内 Java 变化。

### 9.7 Docker 数据为什么看起来还在 C 盘

Docker Desktop 本体、配置文件、锁文件可能仍在 C 盘，这是正常的。重点看 WSL 数据目录是否为 Junction：

```powershell
Get-Item "$env:LOCALAPPDATA\Docker\wsl" | Format-List FullName,Attributes,Target,LinkType
```

期望看到：

```text
LinkType : Junction
Target   : D:\docker\desktop-wsl
```

业务数据则看：

```powershell
Get-ChildItem D:\docker\bigdata\data
```

## 10. 最终验收命令

每次确认环境是否正常，按下面顺序执行：

```powershell
cd D:\bigdatashixun\project
.\scripts\bigdata-docker.cmd status
docker compose exec -T python python src/python/check_bigdata_connections.py
docker compose exec -T python python src/python/check_bigdata_connections.py --spark-job
docker compose exec -T spark-master spark-sql --master spark://spark-master:7077 -e "show databases;"
```

期望结果：

- `status` 显示服务容器正在运行。
- Python 基础检查显示 `Result: 14/14 checks passed`。
- Python Spark 任务检查显示 `Result: 15/15 checks passed`。
- Spark SQL 能输出数据库列表。

如果以上全部通过，说明 Docker 大数据环境可用于后续代码开发和实训。
