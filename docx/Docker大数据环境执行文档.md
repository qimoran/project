# 职途洞察 Docker 大数据环境执行文档

> 旧流程记录：当前最终操作以 `Docker大数据环境最终配置与检查手册.md` 为准。本文件中部分安装/下载辅助脚本命令已经从 `scripts` 目录移除。

本文档用于把 Windows 本地散装的大数据组件改为 Docker Compose 管理。目标是尽量把镜像构建素材、容器数据、MySQL/Redis/HDFS/Spark 持久化数据放到 D 盘。

## 1. 当前方案

| 组件 | Docker 版本/来源 | 端口 |
| --- | --- | --- |
| MySQL | `mysql:8.0.39` | `127.0.0.1:13306 -> 3306` |
| Redis | `redis:5.0.14` | `127.0.0.1:16379 -> 6379` |
| Hadoop | 本地包构建 `hadoop-3.3.6.tar.gz` + Java 8 | HDFS UI `9870`、RPC `9000` |
| Hive | 本地包构建 `hive-4.0.1-bin.tar.gz` + MySQL Connector/J 8.0.33 | Metastore `9083`、HiveServer2 `10000` |
| Spark | 本地包构建 `spark-3.5.1-bin-hadoop3.tgz` + Java 8 | Master `7077`、UI `18080` |
| Python | `python:3.12-slim` + 项目依赖 | 进入容器使用 |

宿主机已经有 MySQL `3306` 和 Redis `6379`，所以 Docker 版刻意映射到 `13306` 和 `16379`，避免端口冲突。

## 2. D 盘目录

默认使用：

```text
D:\docker\bigdata\data
```

数据目录由脚本自动创建：

```text
D:\docker\bigdata\data\mysql
D:\docker\bigdata\data\redis
D:\docker\bigdata\data\hdfs\namenode
D:\docker\bigdata\data\hdfs\datanode
D:\docker\bigdata\data\hadoop-tmp
D:\docker\bigdata\data\spark-events
```

本地安装包会硬链接到：

```text
D:\bigdatashixun\project\docker\build-context\assets
```

硬链接不额外占用一份大文件空间；如果硬链接失败，脚本才会复制。

## 3. Docker 前置条件

当前机器需要 Docker Desktop + WSL2。

你当前代理端口是：

```text
127.0.0.1:7897
```

项目默认会把 Docker 构建代理设置为：

```text
HTTP_PROXY=http://host.docker.internal:7897
HTTPS_PROXY=http://host.docker.internal:7897
```

如果某一步不走代理更快，可以在 `.env` 里把 `HTTP_PROXY`、`HTTPS_PROXY` 清空。

先把 Docker Desktop 安装器下载到 D 盘并验证 Docker Inc 签名：

```powershell
cd D:\bigdatashixun\project
.\scripts\bigdata-docker.cmd download-docker
```

管理员 PowerShell 执行：

```powershell
cd /d D:\bigdatashixun\project
powershell -ExecutionPolicy Bypass -File .\scripts\setup-docker-prereqs-admin.ps1
```

如果提示需要重启，先重启 Windows。重启后打开 Docker Desktop。

如果 Docker 官方 URL 已经发布新版本，`winget show --id Docker.DockerDesktop --exact` 可能还显示上一版 SHA256。此时以 Authenticode 签名为准：签名必须是 `Docker Inc` 且状态为 `Valid`。

建议 Docker Desktop 资源：

```text
Memory: 8GB
CPU: 4
Swap: 4GB
Disk image / data location: D:\docker
```

如果 Docker Desktop 设置界面有磁盘镜像位置选项，把它改到 `D:\docker`。如果没有该选项，也至少保证 Compose 的业务数据在 `D:\docker\bigdata\data`。

## 4. 准备构建素材

普通 PowerShell 执行：

```powershell
cd D:\bigdatashixun\project
.\scripts\bigdata-docker.cmd prepare
```

该步骤会：

- 创建 `.env`；
- 创建 D 盘数据目录；
- 把 `D:\bigdatashixun\安装包` 里的 Hadoop/Hive/Spark 压缩包硬链接到 Docker 构建上下文。

## 5. 启动

只启动轻量基础服务：

```powershell
.\scripts\bigdata-docker.cmd up-core
```

启动完整大数据环境：

```powershell
.\scripts\bigdata-docker.cmd up-all
```

第一次执行会拉取基础镜像并构建自定义镜像，耗时较久。

## 6. 检查

```powershell
.\scripts\bigdata-docker.cmd status
```

浏览器访问：

```text
HDFS:  http://localhost:9870
YARN:  http://localhost:8088
Spark: http://localhost:18080
```

MySQL：

```text
Host: 127.0.0.1
Port: 13306
User: root
Password: root123456
Database: zhitu / hive_metastore
```

Redis：

```text
Host: 127.0.0.1
Port: 16379
```

进入 Python 容器：

```powershell
.\scripts\bigdata-docker.cmd python
```

进入 Beeline：

```powershell
.\scripts\bigdata-docker.cmd beeline
```

进入 Spark Shell：

```powershell
.\scripts\bigdata-docker.cmd spark-shell
```

## 7. 停止

```powershell
.\scripts\bigdata-docker.cmd down
```

该命令会停止并删除容器，但不会删除 D 盘数据目录。

## 8. 常用命令

```powershell
.\scripts\bigdata-docker.cmd check
.\scripts\bigdata-docker.cmd prepare
.\scripts\bigdata-docker.cmd up-core
.\scripts\bigdata-docker.cmd up-all
.\scripts\bigdata-docker.cmd status
.\scripts\bigdata-docker.cmd logs
.\scripts\bigdata-docker.cmd down
```

## 9. 内存建议

你的机器约 14GB 内存，Docker 完整栈能跑实训，但不要长期全开大任务。

推荐：

```text
Docker Desktop memory: 8GB
Spark worker memory: 2GB
Hadoop replication: 1
需要 Hive/Spark 时再启动完整栈
```

如果只是爬虫、MySQL、Redis：

```powershell
.\scripts\bigdata-docker.cmd up-core
```

这样更省内存。
