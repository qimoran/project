# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

职途洞察 —— 大数据专业实践项目：对公开招聘页面进行慢速采集，清洗、分析岗位数据并生成 AI 报告。完整技术栈（MySQL 8.0、Redis 5.0.14、Hadoop 3.3.6、Hive 4.0.1、Spark 3.5.1、Python 3.12）全部通过 Docker Compose 运行（compose 项目名 `zhitu-bigdata`）。当前 `agent` 分支加入了"流程智能体"管线和 Flask 网页看板。文档和代码注释均为中文，面向用户的字符串请保持中文。

## 常用命令

所有控制都通过一个脚本（Windows 宿主机，封装了带全部 profile 的 `docker compose`）：

```powershell
.\scripts\bigdata-docker.cmd up-all    # 启动完整环境（会先执行 prepare 脚本）
.\scripts\bigdata-docker.cmd down      # 全部停止
.\scripts\bigdata-docker.cmd status    # 查看容器状态
.\scripts\bigdata-docker.cmd logs      # 跟踪日志
.\scripts\bigdata-docker.cmd build     # 从 docker/build-context 重新构建镜像
.\scripts\bigdata-docker.cmd python    # 进入 zhitu-python 容器的 bash
.\scripts\bigdata-docker.cmd beeline   # Hive beeline 交互
.\scripts\bigdata-docker.cmd web       # 启动网页看板 http://localhost:5000
.\scripts\bigdata-docker.cmd agent     # 在 python 容器内运行一次流程智能体
```

Python 代码设计为**在容器内运行**：仓库挂载到 `/workspace`，且 `PYTHONPATH=/workspace/src`。宿主机没有虚拟环境。容器内常用：

```bash
python -m career_insight.agent.cli               # 运行一次智能体管线
python -m career_insight.visualization.app       # 手动启动看板
python src/python/check_bigdata_connections.py   # 检查 MySQL/Redis/HDFS/Spark 连通性
```

单元测试在宿主机直接跑（被测代码是纯函数，不依赖容器）：

```powershell
python -m pytest          # 配置在 pytest.ini（pythonpath=src）；pytest 装在 requirements-dev.txt
```

依赖分两层：`src/career_insight/requirements.txt` 是核心包依赖（flask/pymysql/requests/beautifulsoup4）；`docker/build-context/requirements-python.txt` 是镜像构建用的（核心 + demo 脚本的 pyspark/redis）。

宿主机端口：MySQL `13306`（容器内 `mysql:3306`，账号 `zhitu`/`zhitu123456`，库 `zhitu`）、Redis `16379`、HDFS NameNode UI `9870`、YARN `8088`、HiveServer2 `10000`、Spark master UI `18080`、看板 `5000`。

## 架构

核心代码包是 `src/career_insight/`。中心抽象是 `agent/orchestrator.py` 里的**流程智能体管线**（`WorkflowAgent.run`），按固定步骤执行，并把每次运行和每个步骤记录到 MySQL 审计表：

```
采集 (crawlers/selenium_scraper.SlowJobScraper) → raw_jobs (MySQL)
→ 清洗 (data_processing/cleaner.clean_jobs) → agent_clean_jobs
→ 分析 (analysis/trend_analysis.run_salary_and_trend_analysis) → 分析表 + metrics 字典
→ HDFS 同步 (storage/hdfs_handler.sync_agent_outputs) —— 失败只记 warning，不中断
→ AI 报告 (ai_module/recommendation.generate_ai_report) → 存入 MySQL
```

跨文件的关键设计：

- **配置**集中在 `config/settings.py` 的 frozen dataclass `Settings`，全部来自环境变量（由 docker-compose.yml 注入 `python` 和 `web` 容器，也可在仓库根目录 `.env` 中设置）。不要在别处直接读环境变量——需要新配置时给 `Settings` 加字段。
- **MySQL 是唯一事实来源**：`storage/mysql_handler.MySQLStore` 负责建表（`ensure_schema`，只在应用/CLI 启动时调用）、运行/步骤记录、原始与清洗岗位表、分析结果、报告和调度开关。连接按线程复用（`threading.local` + ping 重连）；“先删后插”类写入（`replace_clean_jobs`/`replace_analysis`）走事务，失败自动回滚。看板的所有数据都从它读取。
- **LLM 调用**走 OpenAI 兼容的 `/v1/chat/completions` 接口（`LLM_BASE_URL`、`LLM_MODEL`，默认 `glm-5`）。`LLM_API_KEY` 为空或调用失败时，报告生成会回退到本地规则报告（`used_fallback`）而不是报错——请保留这个兜底行为。
- **采集刻意保持慢速、克制**：只抓取配置的公开 URL（`CRAWL_TARGET_URLS`），带延迟（`CRAWL_DELAY_SECONDS`）；不处理登录、验证码，不绕过反爬。未配置 URL 时管线直接分析已有的 `raw_jobs` 数据而不是失败。
- **网页看板**（`visualization/app.py` + `templates/dashboard.html`）启动时建表、启动 `DailyAgentScheduler` 定时器，提供 JSON API，并可通过 `AgentRunner` 在后台线程触发智能体（用锁保证同时只有一次运行）。前端轮询走轻量的 `/api/agent/status`，只在运行状态变化时拉全量 `/api/dashboard`；echarts 由 `visualization/static/echarts.min.js` 本地提供（加载失败回退 CDN）；所有动态内容入 DOM 前必须经 `escapeHtml` 转义。

`src/python/` 是独立于包的演示/诊断脚本。`docker/build-context/` 存放 Dockerfile 及预下载的安装包和 Python wheel，用于离线构建镜像。`docx/` 是中文安装与使用手册。
