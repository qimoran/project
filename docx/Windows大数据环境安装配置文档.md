# 职途洞察 —— Windows 大数据环境安装配置文档

> 本文档面向「职途洞察」实践项目，指导在 **Windows 10 / 11** 系统下，从零搭建完整的大数据运行环境（爬虫 → 处理 → 存储 → 分析 → 可视化）。
>
> 按本文档**自上而下顺序**安装即可，组件之间存在依赖关系，请勿跳序。

---

## 目录

- [一、版本清单与架构总览](#一版本清单与架构总览)
- [二、安装前准备（务必先读）](#二安装前准备务必先读)
- [三、JDK 8 安装配置](#三jdk-8-安装配置)
- [四、Python 3.12 安装配置](#四python-312-安装配置)
- [五、MySQL 8.0 安装配置](#五mysql-80-安装配置)
- [六、Redis 5.0.14 安装配置](#六redis-5014-安装配置)
- [七、Hadoop 3.3.6 安装配置](#七hadoop-336-安装配置)
- [八、Hive 4.0.1 安装配置](#八hive-401-安装配置)
- [九、Spark 3.5.1 安装配置](#九spark-351-安装配置)
- [十、环境变量总表](#十环境变量总表)
- [十一、服务启动 / 停止顺序](#十一服务启动--停止顺序)
- [十二、安装验证清单](#十二安装验证清单)
- [十三、常见问题 FAQ](#十三常见问题-faq)

---

## 一、版本清单与架构总览

### 1.1 软件版本清单

| 组件 | 版本 | 作用 | 是否必装 |
| --- | --- | --- | --- |
| JDK | **8 (1.8)** | Hadoop / Hive / Spark 的运行基础 | ✅ 必装 |
| Python | **3.12** | 爬虫、数据处理、PySpark、可视化 | ✅ 必装 |
| MySQL | **8.0** | 业务数据存储 + Hive 元数据库 | ✅ 必装 |
| Redis | **5.0.14**（Windows 移植版） | 爬虫去重 / 分布式队列 / 缓存 | ✅ 必装 |
| Hadoop | **3.3.6** | 分布式存储 HDFS + 资源调度 YARN | ✅ 必装 |
| Hive | **4.0.1** | 数据仓库，SQL 分析 | ✅ 必装 |
| Spark | **3.5.1** | 分布式计算引擎（含 PySpark） | ✅ 必装 |
| winutils | 对应 3.3.6 | Hadoop 在 Windows 上运行的补丁 | ✅ 必装 |
| MySQL Connector/J | 8.0.33 | Hive 连接 MySQL 的 JDBC 驱动 | ✅ 必装 |

> ⚠️ **JDK 为什么选 8 而不是更高版本？**
> Hadoop 3.3.6、Hive 4.0.1、Spark 3.5.1 三者**共同稳定支持的版本是 JDK 8**。Hive 4.x 对 JDK 11+ 兼容性较差，为避免踩坑，**统一使用 JDK 8**。

### 1.2 数据流转架构

```
                 ┌─────────────────────────────────────────────────┐
                 │                Windows 主机                      │
                 │                                                  │
  智联招聘网站 ──▶│  ① 爬虫 (Scrapy/BeautifulSoup + Redis 去重队列)   │
                 │            │                                     │
                 │            ▼                                     │
                 │  ② 数据清洗 (Pandas / NumPy)                      │
                 │            │                                     │
                 │     ┌──────┴───────┐                             │
                 │     ▼              ▼                             │
                 │  ③ MySQL 8.0    ③ HDFS (Hadoop 3.3.6)            │
                 │     │              │                             │
                 │     │              ▼                             │
                 │     │       ④ Hive 4.0.1 数仓 ──▶ Spark 3.5.1 计算 │
                 │     │              │                             │
                 │     └──────┬───────┘                             │
                 │            ▼                                     │
                 │  ⑤ 可视化 (ECharts / pyecharts + Flask)          │
                 └─────────────────────────────────────────────────┘
```

---

## 二、安装前准备（务必先读）

### 2.1 硬件建议

| 项目 | 最低 | 推荐 |
| --- | --- | --- |
| 内存 | 8 GB | **16 GB 及以上**（Hadoop+Hive+Spark 同时跑较吃内存） |
| 磁盘 | 预留 30 GB | 预留 50 GB SSD |
| 系统 | Windows 10 64 位 | Windows 11 64 位 |

### 2.2 安装目录规划（关键）

> ❗ **三条铁律，违反任意一条都会导致 Hadoop/Hive/Spark 启动失败：**
> 1. 安装路径**绝对不能包含中文**；
> 2. 安装路径**绝对不能包含空格**（所以不要装在 `C:\Program Files` 下）；
> 3. 路径尽量短。

推荐统一安装到 `D:\bigdata` 下，目录规划如下（先手动创建好这些空目录）：

```
D:\bigdata\
├── Java\jdk1.8.0_xxx              # JDK 8
├── hadoop-3.3.6\                  # Hadoop
├── apache-hive-4.0.1-bin\         # Hive
├── spark-3.5.1-bin-hadoop3\       # Spark
└── data\                          # 各组件的数据目录
    └── hadoop\
        ├── tmp\
        ├── namenode\
        └── datanode\
```

> Python、MySQL、Redis 可以使用各自安装程序的默认路径，但也建议放在无空格目录。

### 2.3 通用注意事项

- **所有涉及环境变量的操作，配置完后必须新开一个命令行窗口（CMD/PowerShell）才能生效。**
- 后续命令行示例中，CMD 与 PowerShell 通用的写死了路径；如遇 PowerShell 报错，可直接用 **CMD（命令提示符）**运行 Hadoop/Hive 命令，兼容性最好。
- Hadoop/Hive 启动脚本是 `.cmd` 批处理，**建议统一在 CMD 中运行**。
- 部分操作（如格式化、注册服务）需要**以管理员身份运行**命令行。
- 杀毒软件 / Windows Defender 可能误删 `winutils.exe`，如遇文件莫名消失，请将 `D:\bigdata` 加入白名单。

### 2.4 解压 `.tar.gz` / `.tgz` 文件

Hadoop、Hive、Spark 的官方包都是 `.tar.gz`/`.tgz` 格式。Windows 10/11 已自带 `tar` 命令，在 CMD 中即可解压：

```cmd
tar -zxvf hadoop-3.3.6.tar.gz -C D:\bigdata
```

也可使用 [7-Zip](https://www.7-zip.org/) 解压（需解压两次：`.tar.gz` → `.tar` → 文件夹）。

---

## 三、JDK 8 安装配置

### 3.1 下载

任选其一（免费，推荐第一个）：

- **Adoptium Temurin 8**：<https://adoptium.net/temurin/releases/?version=8&os=windows&arch=x64>（选择 `.msi` 安装包）
- Oracle JDK 8：<https://www.oracle.com/java/technologies/downloads/#java8-windows>（需注册 Oracle 账号）

### 3.2 安装

- 安装时**把安装路径改为无空格目录**，例如 `D:\bigdata\Java\jdk1.8.0_xxx`。
- 若使用 Oracle 安装包默认装到了 `C:\Program Files\Java\...`，**强烈建议卸载重装到 `D:\bigdata\Java\`**，否则 Hadoop 配置 `JAVA_HOME` 会非常麻烦。

### 3.3 配置环境变量

`Win + R` → 输入 `sysdm.cpl` → 「高级」→「环境变量」→ 在「系统变量」中：

| 变量名 | 变量值（按你的实际安装路径填写） |
| --- | --- |
| `JAVA_HOME` | `D:\bigdata\Java\jdk1.8.0_xxx` |

然后编辑系统变量 `Path`，**新增**一项：

```
%JAVA_HOME%\bin
```

### 3.4 验证

新开 CMD 窗口：

```cmd
java -version
javac -version
echo %JAVA_HOME%
```

出现类似 `java version "1.8.0_xxx"` 即成功。

---

## 四、Python 3.12 安装配置

### 4.1 下载与安装

下载地址：<https://www.python.org/downloads/release/python-3120/>（选择 *Windows installer (64-bit)*）

安装时：

- ✅ **务必勾选 `Add python.exe to PATH`**（最重要！）
- 选择 `Customize installation` → 勾选 `pip`、`py launcher`；
- 安装路径建议改为无空格目录，例如 `D:\bigdata\Python312`。

### 4.2 验证

```cmd
python --version       :: 应输出 Python 3.12.x
pip --version
```

### 4.3 配置 pip 国内镜像（加速依赖下载）

```cmd
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4.4 创建项目虚拟环境（推荐）

在项目目录下创建独立虚拟环境，避免污染全局：

```cmd
cd /d D:\bigdatashixun\project
python -m venv venv
venv\Scripts\activate
```

激活后命令行前会出现 `(venv)` 字样。

### 4.5 安装项目依赖

在项目根目录新建 `requirements.txt`，内容如下：

```text
# ===== 爬虫 =====
scrapy>=2.11            # 2.11+ 才支持 Python 3.12
beautifulsoup4
lxml
requests
scrapy-redis            # 基于 Redis 的分布式爬虫/去重（可选）
fake-useragent

# ===== 数据处理与分析 =====
pandas
numpy

# ===== 数据库 =====
pymysql                 # 连接 MySQL
sqlalchemy              # 配合 pandas.to_sql 使用
redis                   # 连接 Redis

# ===== 大数据 =====
pyspark==3.5.1
findspark               # 在脚本中定位 SPARK_HOME

# ===== 可视化 =====
pyecharts               # Python 端 ECharts 封装
flask                   # 可视化大屏后端（可选）
```

安装：

```cmd
pip install -r requirements.txt
```

> ⚠️ **PySpark 与 Python 3.12 的兼容性提醒（重要）**
> PySpark 3.5.1 官方测试覆盖到 Python 3.11，在 **Python 3.12 上可能因标准库移除 `distutils` 而报错**
> （`ModuleNotFoundError: No module named 'distutils'`）。
> **解决办法（任选）：**
> 1. 安装 setuptools 提供 distutils 兼容层（多数情况可解决）：`pip install setuptools` ；
> 2. 若仍报错，**单独为 Spark 任务建一个 Python 3.11 环境**（用 Anaconda/Miniconda 最方便：`conda create -n pyspark python=3.11`），其余爬虫/分析仍用 3.12。

---

## 五、MySQL 8.0 安装配置

### 5.1 下载

MySQL Installer：<https://dev.mysql.com/downloads/installer/>
选择 `mysql-installer-community-8.0.x.msi`（体积较大的完整版）。

### 5.2 安装

1. 选择安装类型 `Custom` 或 `Server only`；
2. 安装 **MySQL Server 8.0.x**；
3. 配置阶段：
   - Config Type 选 `Development Computer`；
   - 端口保持默认 **3306**；
   - Authentication Method 选 **`Use Strong Password Encryption`**（默认）；
   - 设置 **root 密码**（务必牢记，例如 `123456`，后续 Hive 要用）；
   - 勾选 `Configure MySQL Server as a Windows Service`，服务名默认 `MySQL80`，勾选开机自启。

### 5.3 配置环境变量（可选，方便命令行使用）

MySQL 默认安装在 `C:\Program Files\MySQL\MySQL Server 8.0`。把其 `bin` 目录加入 `Path`：

```
C:\Program Files\MySQL\MySQL Server 8.0\bin
```

### 5.4 验证与初始化

```cmd
mysql -u root -p
```

输入密码后进入 MySQL，执行以下语句为项目准备数据库（字符集用 utf8mb4 防止中文乱码）：

```sql
-- 业务数据库
CREATE DATABASE IF NOT EXISTS zhitu DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

-- Hive 元数据库（第八节会用到，先建好）
CREATE DATABASE IF NOT EXISTS hive_metastore DEFAULT CHARACTER SET latin1;

SHOW DATABASES;
```

> 📌 Hive 元数据库的字符集**必须是 `latin1`**，否则 schematool 初始化时可能报错。

### 5.5 管理服务

```cmd
net start MySQL80      :: 启动
net stop MySQL80       :: 停止
```

---

## 六、Redis 5.0.14 安装配置

> Redis 官方不提供 Windows 版本。`5.0.14` 对应的是社区维护的 **tporadowski Windows 移植版**，与项目要求版本一致。

### 6.1 下载

<https://github.com/tporadowski/redis/releases>
下载 `Redis-x64-5.0.14.1.zip`（绿色解压版，推荐）或 `Redis-x64-5.0.14.1.msi`（安装版）。

### 6.2 安装（以 zip 解压版为例）

1. 解压到无空格目录，例如 `D:\bigdata\Redis-5.0.14`；
2. 编辑该目录下的 `redis.windows.conf`，按需修改（可选）：
   - 设置访问密码：找到 `# requirepass foobared`，改为 `requirepass 123456`（去掉 `#`）；
   - 绑定本机：`bind 127.0.0.1`。

### 6.3 启动 Redis 服务

**方式一：临时启动（前台运行，关闭窗口即停止）**

```cmd
cd /d D:\bigdata\Redis-5.0.14
redis-server.exe redis.windows.conf
```

看到 Redis 的 LOGO 和 `Ready to accept connections` 即启动成功。

**方式二：注册为 Windows 服务（开机自启，推荐）**

以**管理员身份**打开 CMD：

```cmd
cd /d D:\bigdata\Redis-5.0.14
redis-server.exe --service-install redis.windows.conf --service-name Redis
redis-server.exe --service-start --service-name Redis
```

### 6.4 配置环境变量（可选）

把 `D:\bigdata\Redis-5.0.14` 加入 `Path`，方便任意位置调用 `redis-cli`。

### 6.5 验证

```cmd
redis-cli
127.0.0.1:6379> ping
PONG
```

若设置了密码：`redis-cli -a 123456`，再 `ping`。

---

## 七、Hadoop 3.3.6 安装配置

> Hadoop 是后续 Hive、Spark 的基础，必须**先装好并启动成功**。

### 7.1 下载

- Hadoop 本体：<https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz>
- **winutils 补丁**（Windows 必需）：
  - <https://github.com/kontext-tech/winutils>（包含 `hadoop-3.3.6/bin`）
  - 备用：<https://github.com/cdarlint/winutils>
  - 需要的两个核心文件：**`winutils.exe`** 和 **`hadoop.dll`**

### 7.2 解压

```cmd
tar -zxvf hadoop-3.3.6.tar.gz -C D:\bigdata
```

解压后得到 `D:\bigdata\hadoop-3.3.6`。

### 7.3 打补丁 winutils

1. 从 winutils 仓库下载 `hadoop-3.3.6/bin` 目录下的所有文件；
2. 将其中的 **`winutils.exe`、`hadoop.dll`** 等文件**覆盖**到 `D:\bigdata\hadoop-3.3.6\bin`；
3. 同时把 `hadoop.dll` **复制一份**到 `C:\Windows\System32`（解决 native 库加载问题）。

### 7.4 配置环境变量

系统变量新增：

| 变量名 | 变量值 |
| --- | --- |
| `HADOOP_HOME` | `D:\bigdata\hadoop-3.3.6` |

`Path` 中新增两项：

```
%HADOOP_HOME%\bin
%HADOOP_HOME%\sbin
```

### 7.5 修改配置文件

进入 `D:\bigdata\hadoop-3.3.6\etc\hadoop\`，依次修改以下文件。

#### ① `hadoop-env.cmd`

找到 `set JAVA_HOME=...` 一行，改成你的 JDK 路径（**注意是 cmd 文件，用 `set`**）：

```bat
set JAVA_HOME=D:\bigdata\Java\jdk1.8.0_xxx
```

#### ② `core-site.xml`

```xml
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:9000</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>/D:/bigdata/data/hadoop/tmp</value>
    </property>
</configuration>
```

#### ③ `hdfs-site.xml`

```xml
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>/D:/bigdata/data/hadoop/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>/D:/bigdata/data/hadoop/datanode</value>
    </property>
</configuration>
```

> 📌 Windows 下路径写法为 `/D:/bigdata/...`（盘符前加 `/`，用正斜杠）。

#### ④ `mapred-site.xml`

```xml
<configuration>
    <property>
        <name>mapreduce.framework.name</name>
        <value>yarn</value>
    </property>
</configuration>
```

#### ⑤ `yarn-site.xml`

```xml
<configuration>
    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>
    <property>
        <name>yarn.nodemanager.aux-services.mapreduce.shuffle.class</name>
        <value>org.apache.hadoop.mapred.ShuffleHandler</value>
    </property>
</configuration>
```

### 7.6 格式化 NameNode（仅首次执行一次）

> ⚠️ 格式化只在**第一次安装时执行一次**。重复格式化会导致 DataNode 启动失败（需手动清空 data 目录）。

新开 CMD：

```cmd
hdfs namenode -format
```

出现 `successfully formatted` 即成功。

### 7.7 启动 Hadoop

```cmd
:: 启动 HDFS（会弹出 NameNode、DataNode 两个窗口，不要关闭）
start-dfs.cmd

:: 启动 YARN（会弹出 ResourceManager、NodeManager 两个窗口，不要关闭）
start-yarn.cmd
```

### 7.8 验证

```cmd
jps
```

应能看到 4 个进程（外加 Jps）：

```
NameNode
DataNode
ResourceManager
NodeManager
```

浏览器访问 Web UI：

| 服务 | 地址 |
| --- | --- |
| HDFS NameNode | <http://localhost:9870> |
| YARN ResourceManager | <http://localhost:8088> |

测试 HDFS 读写：

```cmd
hdfs dfs -mkdir /test
hdfs dfs -ls /
```

### 7.9 停止 Hadoop

```cmd
stop-yarn.cmd
stop-dfs.cmd
```

---

## 八、Hive 4.0.1 安装配置

> Hive 依赖 **Hadoop（HDFS 必须已启动）** 和 **MySQL（存放元数据）**，请确保第五、七节已完成。

> ### ⚠️ 关于 Hive 在原生 Windows 上运行的重要说明（请先阅读）
>
> Apache Hive **新版本（3.x/4.x）对原生 Windows 的支持很弱**，官方逐步移除了 Windows 的 `.cmd` 启动脚本，`bin` 目录可能**只剩 Linux 的 shell 脚本**。
>
> **请先检查** `apache-hive-4.0.1-bin\bin` 目录里是否存在 `hive.cmd`、`schematool.cmd` 等 `.cmd` 文件：
> - **若存在 `.cmd` 脚本** → 按本节步骤在原生 Windows 上配置即可；
> - **若只有无后缀的 shell 脚本（无 `.cmd`）** → 原生 Windows 无法直接启动 Hive，请改用下面任一**可靠替代方案**：
>   1. 🥇 **WSL2（推荐）**：在 Windows 上开启「适用于 Linux 的子系统」，安装 Ubuntu，在 Linux 环境里跑 Hadoop+Hive+Spark，稳定无坑。WSL2 本身就是 Windows 的官方功能，完全符合「在 Windows 下搭建」的要求。
>   2. **改用 Hive 3.1.2**：该版本在原生 Windows 上有成熟的 `.cmd` 脚本与大量教程，可与 Hadoop 3.3.6 配合，用于学习/课程实践完全够用。
>
> 下面以**原生 Windows + Hive 4.0.1** 为主线说明配置；命令在 WSL2/Linux 下把 `.cmd` 去掉即同样适用。

### 8.1 下载

- Hive：<https://archive.apache.org/dist/hive/hive-4.0.1/apache-hive-4.0.1-bin.tar.gz>
- MySQL JDBC 驱动（Connector/J）：<https://dev.mysql.com/downloads/connector/j/>
  下载 *Platform Independent* 版，解压取出 `mysql-connector-j-8.0.33.jar`。

### 8.2 解压

```cmd
tar -zxvf apache-hive-4.0.1-bin.tar.gz -C D:\bigdata
```

得到 `D:\bigdata\apache-hive-4.0.1-bin`。

### 8.3 配置环境变量

| 变量名 | 变量值 |
| --- | --- |
| `HIVE_HOME` | `D:\bigdata\apache-hive-4.0.1-bin` |

`Path` 中新增：

```
%HIVE_HOME%\bin
```

### 8.4 放置 MySQL 驱动

把 `mysql-connector-j-8.0.33.jar` 复制到：

```
D:\bigdata\apache-hive-4.0.1-bin\lib\
```

### 8.5 新建配置文件 `hive-site.xml`

在 `D:\bigdata\apache-hive-4.0.1-bin\conf\` 下新建 `hive-site.xml`（注意 JDBC 地址里的 `&` 必须写成 `&amp;`，密码改成你的 MySQL root 密码）：

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <!-- 元数据库连接 -->
    <property>
        <name>javax.jdo.option.ConnectionURL</name>
        <value>jdbc:mysql://localhost:3306/hive_metastore?createDatabaseIfNotExist=true&amp;useSSL=false&amp;allowPublicKeyRetrieval=true&amp;characterEncoding=UTF-8&amp;serverTimezone=Asia/Shanghai</value>
    </property>
    <property>
        <name>javax.jdo.option.ConnectionDriverName</name>
        <value>com.mysql.cj.jdbc.Driver</value>
    </property>
    <property>
        <name>javax.jdo.option.ConnectionUserName</name>
        <value>root</value>
    </property>
    <property>
        <name>javax.jdo.option.ConnectionPassword</name>
        <value>123456</value>
    </property>

    <!-- 数据仓库在 HDFS 上的目录 -->
    <property>
        <name>hive.metastore.warehouse.dir</name>
        <value>/user/hive/warehouse</value>
    </property>

    <!-- 关闭元数据版本校验，避免启动报错 -->
    <property>
        <name>hive.metastore.schema.verification</name>
        <value>false</value>
    </property>

    <!-- 单机本地模式相关 -->
    <property>
        <name>hive.server2.enable.doAs</name>
        <value>false</value>
    </property>
    <property>
        <name>hive.server2.thrift.port</name>
        <value>10000</value>
    </property>
</configuration>
```

### 8.6 在 HDFS 上创建 Hive 所需目录

确保 Hadoop 已启动，然后执行：

```cmd
hdfs dfs -mkdir -p /user/hive/warehouse
hdfs dfs -mkdir -p /tmp
hdfs dfs -chmod -R 777 /user/hive/warehouse
hdfs dfs -chmod -R 777 /tmp
```

### 8.7 初始化元数据库

```cmd
schematool -dbType mysql -initSchema
```

> 若提示 `schematool 不是内部命令`，说明该版本没有 `.cmd` 脚本，请参照 8 节开头的替代方案（WSL2 / Hive 3.1.2）。
> 出现 `schemaTool completed` 即初始化成功，此时 MySQL 的 `hive_metastore` 库中会生成几十张元数据表。

### 8.8 启动 Hive 服务

Hive 4.x 推荐使用 **HiveServer2 + Beeline** 方式：

```cmd
:: 窗口一：启动元数据服务（保持开启）
hive --service metastore

:: 窗口二：启动 HiveServer2（保持开启）
hive --service hiveserver2
```

### 8.9 验证

新开窗口，用 Beeline 连接：

```cmd
beeline -u jdbc:hive2://localhost:10000 -n root
```

连接成功后执行 SQL 测试：

```sql
SHOW DATABASES;
CREATE TABLE test_t (id INT, name STRING);
INSERT INTO test_t VALUES (1, 'hello hive');
SELECT * FROM test_t;
```

也可通过 Web UI 查看 HiveServer2：<http://localhost:10002>

---

## 九、Spark 3.5.1 安装配置

> Spark 复用 Hadoop 的 `winutils`，请确保第七节已完成。

### 9.1 下载

<https://archive.apache.org/dist/spark/spark-3.5.1/spark-3.5.1-bin-hadoop3.tgz>
（选 **`bin-hadoop3`** 版，与 Hadoop 3.x 匹配）

### 9.2 解压

```cmd
tar -zxvf spark-3.5.1-bin-hadoop3.tgz -C D:\bigdata
```

得到 `D:\bigdata\spark-3.5.1-bin-hadoop3`。

### 9.3 配置环境变量

| 变量名 | 变量值 |
| --- | --- |
| `SPARK_HOME` | `D:\bigdata\spark-3.5.1-bin-hadoop3` |
| `PYSPARK_PYTHON` | `python`（或你的 python.exe 完整路径） |

`Path` 中新增：

```
%SPARK_HOME%\bin
```

> 📌 `PYSPARK_PYTHON` 用于指定 PySpark 调用的 Python 解释器；若用第 4.5 节的 Python 3.11 专用环境跑 Spark，请把它指向那个环境的 `python.exe`。

### 9.4 验证（本地模式）

#### ① Scala 交互式

```cmd
spark-shell
```

出现 Spark 的 ASCII LOGO 和 `scala>` 提示符即成功，输入 `:quit` 退出。

#### ② PySpark 交互式

```cmd
pyspark
```

出现 `>>>` 提示符后测试：

```python
spark.range(5).show()
```

#### ③ 提交示例任务

```cmd
spark-submit --class org.apache.spark.examples.SparkPi %SPARK_HOME%\examples\jars\spark-examples_2.12-3.5.1.jar 10
```

运行任务时可访问 Spark Web UI：<http://localhost:4040>

### 9.5 Spark 集成 Hive（可选，用于 Spark SQL 读写 Hive 表）

1. 把 Hive 的配置文件复制给 Spark：
   将 `D:\bigdata\apache-hive-4.0.1-bin\conf\hive-site.xml`
   复制到 `D:\bigdata\spark-3.5.1-bin-hadoop3\conf\`。
2. 把 MySQL 驱动复制给 Spark：
   将 `mysql-connector-j-8.0.33.jar` 复制到 `D:\bigdata\spark-3.5.1-bin-hadoop3\jars\`。
3. 在 PySpark 中启用 Hive 支持：

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("zhitu") \
    .enableHiveSupport() \
    .getOrCreate()

spark.sql("SHOW DATABASES").show()
```

---

## 十、环境变量总表

配置完所有组件后，系统变量应包含下表内容（请对照检查）：

| 变量名 | 值 |
| --- | --- |
| `JAVA_HOME` | `D:\bigdata\Java\jdk1.8.0_xxx` |
| `HADOOP_HOME` | `D:\bigdata\hadoop-3.3.6` |
| `HIVE_HOME` | `D:\bigdata\apache-hive-4.0.1-bin` |
| `SPARK_HOME` | `D:\bigdata\spark-3.5.1-bin-hadoop3` |
| `PYSPARK_PYTHON` | `python` |

`Path` 中应包含（顺序不限）：

```
%JAVA_HOME%\bin
%HADOOP_HOME%\bin
%HADOOP_HOME%\sbin
%HIVE_HOME%\bin
%SPARK_HOME%\bin
C:\Program Files\MySQL\MySQL Server 8.0\bin
D:\bigdata\Redis-5.0.14
D:\bigdata\Python312
D:\bigdata\Python312\Scripts
```

> 💡 配置完务必**重启命令行窗口**（或注销/重启电脑）使变量生效。

---

## 十一、服务启动 / 停止顺序

> 组件间有依赖关系，**启动按从上到下，停止按从下到上**。

### 启动顺序

```cmd
:: 1. 启动 MySQL（若已设为开机自启可跳过）
net start MySQL80

:: 2. 启动 Redis（若已注册服务可跳过）
net start Redis

:: 3. 启动 Hadoop（HDFS + YARN）
start-dfs.cmd
start-yarn.cmd

:: 4. 启动 Hive 服务（两个独立窗口）
hive --service metastore
hive --service hiveserver2

:: 5. Spark 为按需运行，无需常驻启动
```

### 停止顺序

```cmd
:: 1. 关闭 Hive 两个服务窗口（Ctrl+C 或直接关窗口）
:: 2. 停止 Hadoop
stop-yarn.cmd
stop-dfs.cmd
:: 3. 停止 Redis / MySQL（如需）
net stop Redis
net stop MySQL80
```

---

## 十二、安装验证清单

逐项打勾，全部通过即环境搭建完成：

| # | 验证命令 / 操作 | 预期结果 |
| --- | --- | --- |
| 1 | `java -version` | 显示 1.8.0_xxx |
| 2 | `python --version` | 显示 Python 3.12.x |
| 3 | `pip list` | 含 scrapy、pandas、pyspark 等 |
| 4 | `mysql -u root -p` 登录并 `SHOW DATABASES;` | 含 `zhitu`、`hive_metastore` |
| 5 | `redis-cli ping` | 返回 `PONG` |
| 6 | `jps` | 含 NameNode/DataNode/ResourceManager/NodeManager |
| 7 | 访问 <http://localhost:9870> | HDFS Web UI 正常 |
| 8 | 访问 <http://localhost:8088> | YARN Web UI 正常 |
| 9 | `beeline -u jdbc:hive2://localhost:10000 -n root` 执行 `SHOW DATABASES;` | 正常返回 |
| 10 | `spark-shell` / `pyspark` | 进入交互式且能 `show()` 数据 |

---

## 十三、常见问题 FAQ

**Q1：`hdfs namenode -format` 后 DataNode 启动失败？**
A：多因重复格式化导致 namenode/datanode 的 clusterID 不一致。删除 `D:\bigdata\data\hadoop` 下的 `namenode`、`datanode`、`tmp` 三个目录里的内容，重新 `format` 一次。

**Q2：启动 Hadoop 报 `JAVA_HOME is incorrectly set` 或找不到 Java？**
A：① 检查 `hadoop-env.cmd` 里 `set JAVA_HOME=` 路径是否正确；② 确保 JDK 路径**无空格**；③ 若必须装在 `C:\Program Files\Java`，可用短路径 `C:\PROGRA~1\Java\jdk1.8.0_xxx`。

**Q3：报错 `winutils.exe` 找不到 / `UnsatisfiedLinkError: ...NativeIO`？**
A：① 确认 `winutils.exe`、`hadoop.dll` 已放入 `%HADOOP_HOME%\bin`；② 把 `hadoop.dll` 复制到 `C:\Windows\System32`；③ 确认下载的是对应 **3.3.6** 版本的 winutils；④ 检查是否被杀毒软件删除。

**Q4：`schematool 不是内部或外部命令` / Hive 无法启动？**
A：Hive 4.0.1 原生 Windows 缺少 `.cmd` 脚本。请参照[第八节开头说明](#八hive-401-安装配置)，改用 **WSL2** 或 **Hive 3.1.2**。

**Q5：Hive 初始化报字符集 / 外键错误？**
A：确保 MySQL 中 `hive_metastore` 库的字符集为 **`latin1`**：`ALTER DATABASE hive_metastore CHARACTER SET latin1;`

**Q6：PySpark 报 `No module named 'distutils'`？**
A：Python 3.12 移除了 distutils。执行 `pip install setuptools`；若仍不行，单独建 Python 3.11 环境跑 Spark（见 [4.5 节](#45-安装项目依赖)）。

**Q7：MySQL 8 连接报 `Public Key Retrieval is not allowed`？**
A：JDBC URL 中加上 `allowPublicKeyRetrieval=true&useSSL=false`（本文档的 hive-site.xml 已包含）。

**Q8：端口被占用（3306/6379/9000/9870/8088/10000）？**
A：用 `netstat -ano | findstr 端口号` 查占用进程 PID，再 `taskkill /PID xxx /F` 结束，或修改对应组件端口配置。

**Q9：命令行中文乱码？**
A：CMD 执行 `chcp 65001` 切换到 UTF-8 编码。

---

> 📎 **文档维护建议**：实际安装时，请把各组件**真实的安装路径、版本小号、root 密码**回填到本文档，方便团队成员复用与排错。
>
> 搭建顺序回顾：**JDK → Python → MySQL → Redis → Hadoop → Hive → Spark**。祝搭建顺利！🚀
