# Docker 大数据环境下载与验证说明

> 旧流程记录：当前最终操作以 `Docker大数据环境最终配置与检查手册.md` 为准。本文件中部分安装/下载辅助脚本命令已经从 `scripts` 目录移除。

本文档记录当前已经准备好的 Docker 大数据环境文件，以及你后续如何验证。

## 1. 已下载/已准备内容

### Docker Desktop 安装器

路径：

```text
D:\docker\installers\Docker Desktop Installer.exe
```

版本：

```text
Docker Desktop 4.77.0.228796
```

SHA256：

```text
5B866599F0DE9208F4594D64AA33658FA55CBDD64E0DB13648CFFE12C91795D2
```

签名状态：

```text
Valid
Signer: Docker Inc
```

说明：Docker 官方下载地址当前返回的是 4.77.0，winget 清单还停在 4.76.0，所以 SHA256 和 winget 显示的不一致。当前文件已通过 Windows Authenticode 签名验证，签名方是 Docker Inc。

### 大数据安装包

原始安装包位置：

```text
D:\bigdatashixun\安装包
```

Docker 构建素材位置：

```text
D:\bigdatashixun\project\docker\build-context\assets
```

已准备：

```text
hadoop-3.3.6.tar.gz
hive-4.0.1-bin.tar.gz
spark-3.5.1-bin-hadoop3.tgz
mysql-connector-j-8.0.33.jar
```

其中 Hadoop/Hive/Spark 是从你的安装包目录硬链接过来的，基本不额外占用 D 盘空间。

MySQL Connector/J 8.0.33 已下载并通过 Maven Central SHA1 校验：

```text
9E64D997873ABC4318620264703D3FDB6B02DD5A
```

### D 盘数据目录

Docker 容器数据默认放在：

```text
D:\docker\bigdata\data
```

已创建：

```text
D:\docker\bigdata\data\mysql
D:\docker\bigdata\data\redis
D:\docker\bigdata\data\hdfs
D:\docker\bigdata\data\hadoop-tmp
D:\docker\bigdata\data\spark-events
```

## 2. 已生成的项目文件

核心文件：

```text
D:\bigdatashixun\project\docker-compose.yml
D:\bigdatashixun\project\.env
D:\bigdatashixun\project\.env.example
```

管理脚本：

```text
D:\bigdatashixun\project\scripts\bigdata-docker.cmd
D:\bigdatashixun\project\scripts\docker-bigdata.ps1
D:\bigdatashixun\project\scripts\prepare-docker-bigdata.ps1
D:\bigdatashixun\project\scripts\download-docker-desktop.ps1
D:\bigdatashixun\project\scripts\setup-docker-prereqs-admin.ps1
D:\bigdatashixun\project\scripts\check-docker-prereqs.ps1
```

详细执行文档：

```text
D:\bigdatashixun\project\docx\Docker大数据环境执行文档.md
```

## 3. 代理配置

你的代理端口：

```text
127.0.0.1:7897
```

`.env` 已配置 Docker 构建阶段代理：

```text
HTTP_PROXY=http://host.docker.internal:7897
HTTPS_PROXY=http://host.docker.internal:7897
NO_PROXY=localhost,127.0.0.1,::1,host.docker.internal,mysql,redis,namenode,datanode,resourcemanager,nodemanager,hive-metastore,hiveserver2,spark-master,spark-worker,python
```

如果后续某一步直连更快，可以临时把 `.env` 里的 `HTTP_PROXY` 和 `HTTPS_PROXY` 留空。

## 4. 你可以先验证这些命令

在普通 PowerShell 中执行：

```powershell
cd D:\bigdatashixun\project
.\scripts\bigdata-docker.cmd check
.\scripts\bigdata-docker.cmd prepare
.\scripts\bigdata-docker.cmd download-docker
```

预期：

- `check` 会显示当前 Docker/WSL 状态；
- `prepare` 会确认 D 盘数据目录和构建素材；
- `download-docker` 会确认 Docker Desktop 安装器签名有效。

## 5. 安装 Docker Desktop

这一步需要管理员权限。

用管理员 PowerShell 执行：

```powershell
cd D:\bigdatashixun\project
powershell -ExecutionPolicy Bypass -File .\scripts\setup-docker-prereqs-admin.ps1
```

这个脚本会：

- 启用 WSL；
- 启用 Virtual Machine Platform；
- 设置 WSL2；
- 写入 `.wslconfig`，限制 Docker/WSL 使用 8GB 内存、4 核 CPU、4GB swap；
- 使用 D 盘已下载且签名有效的 Docker Desktop 安装器；
- 尽量把 Docker 安装和 WSL 数据目录放到 D 盘。

如果 Windows 提示重启，先重启。

## 6. Docker 安装后启动环境

Docker Desktop 正常启动后，在项目目录执行：

只启动 MySQL + Redis：

```powershell
.\scripts\bigdata-docker.cmd up-core
```

启动完整大数据环境：

```powershell
.\scripts\bigdata-docker.cmd up-all
```

查看状态：

```powershell
.\scripts\bigdata-docker.cmd status
```

停止：

```powershell
.\scripts\bigdata-docker.cmd down
```

## 7. 后续访问地址

Docker 启动后：

```text
MySQL: 127.0.0.1:13306
Redis: 127.0.0.1:16379
HDFS UI: http://localhost:9870
YARN UI: http://localhost:8088
Spark UI: http://localhost:18080
HiveServer2: jdbc:hive2://localhost:10000
```

## 8. 当前限制

当前还没有安装 Docker CLI，所以还不能提前拉取 Docker 镜像，也不能构建镜像。等 Docker Desktop 安装并启动后，执行：

```powershell
.\scripts\bigdata-docker.cmd up-all
```

它会自动拉取基础镜像并构建 Hadoop/Hive/Spark/Python 镜像。
