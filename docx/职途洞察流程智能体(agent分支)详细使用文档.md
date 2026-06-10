# 职途洞察流程智能体(agent 分支)详细使用文档

## 1. 文档定位

本文档只对应本项目的 `agent` 分支。

`agent` 分支是在老师主线项目基础上增加的个人增强版本，核心目标是把原来的大数据就业分析项目升级为一个可运行、可展示、可复盘的流程智能体。它不替代老师的 `main` 分支进度，而是用于你自己继续加 AI、智能体、自动化分析和展示能力。

建议分支分工如下：

| 分支 | 用途 | 建议操作 |
| --- | --- | --- |
| `main` | 老师课堂进度、基础项目版本 | 只同步老师进度，少直接改 |
| `agent` | 你的个人智能体版本 | 添加 AI、自动化、页面和文档 |

## 2. agent 分支新增了什么

`agent` 分支主要增加了以下能力：

1. 流程智能体：自动串联采集、清洗、分析、HDFS 同步、AI 报告生成。
2. Web 看板：通过 `http://localhost:5000` 查看运行状态、步骤日志、分析图表和 AI 报告。
3. 云端大模型报告：调用 `https://www.aidawan.fun/v1/chat/completions` 生成中文 Markdown 分析报告。
4. 本地兜底报告：如果没有配置 API Key 或云端模型失败，仍可生成本地规则报告，保证流程不崩。
5. MySQL 运行记录：保存每次智能体运行、步骤状态、分析结果和报告。
6. HDFS 同步：把清洗后的岗位数据和分析指标写入 HDFS，保留大数据链路展示价值。
7. 定时开关：Web 页面可配置每日运行时间，适合演示“智能体定时执行”能力。

## 3. 当前推荐目录结构

建议你本地长期保持两个文件夹：

```text
D:\bigdatashixun\project       # agent 分支，你自己的智能体版本
D:\bigdatashixun\project-main  # main 分支，老师进度版本
```

当前这份文档位于：

```text
D:\bigdatashixun\project\docx\职途洞察流程智能体(agent分支)详细使用文档.md
```

## 4. 智能体整体流程

一次完整智能体运行包含 5 个主要步骤：

```text
1. crawl_jobs
   慢速采集配置的公开岗位页面，写入 raw_jobs。

2. clean_jobs
   标准化岗位名称、城市、薪资、学历、经验、技能等字段。

3. run_analysis
   聚合城市薪资、技能热度、学历分布、经验分布、行业分布。

4. sync_hdfs
   把清洗数据和指标同步到 HDFS。

5. generate_ai_report
   调用云端兼容模型生成中文分析报告；失败时使用本地兜底报告。
```

运行完成后，看板会显示：

| 内容 | 说明 |
| --- | --- |
| 最近运行 | 运行编号、状态、触发方式、运行消息 |
| 步骤日志 | 每个步骤的成功、警告或失败原因 |
| 分析图表 | 城市薪资、技能热度、学历和经验分布 |
| AI 报告 | 大模型生成的就业分析 Markdown 报告 |

## 5. 核心代码位置

| 文件 | 作用 |
| --- | --- |
| `src/career_insight/agent/orchestrator.py` | 流程智能体主编排逻辑 |
| `src/career_insight/agent/cli.py` | 命令行运行入口 |
| `src/career_insight/agent/scheduler.py` | 每日定时运行调度 |
| `src/career_insight/crawlers/selenium_scraper.py` | 慢速公开页面采集 |
| `src/career_insight/data_processing/cleaner.py` | 岗位清洗和标准化 |
| `src/career_insight/analysis/salary_analysis.py` | 薪资、技能、学历、经验分析 |
| `src/career_insight/storage/mysql_handler.py` | MySQL 表结构和读写 |
| `src/career_insight/storage/hdfs_handler.py` | HDFS 输出同步 |
| `src/career_insight/ai_module/llm_chatbot.py` | 云端模型 Chat Completions 客户端 |
| `src/career_insight/ai_module/recommendation.py` | AI 报告 prompt 和兜底报告 |
| `src/career_insight/visualization/app.py` | Flask Web 看板 |
| `src/career_insight/config/settings.py` | 环境变量配置读取 |

## 6. 启动前检查

先确认当前目录和分支：

```powershell
cd D:\bigdatashixun\project
git status
git branch --show-current
```

正常应该显示：

```text
agent
```

如果不是 `agent`，切换：

```powershell
git switch agent
```

## 7. Docker 启动方式

启动基础大数据环境：

```powershell
docker compose up -d
```

启动或重建智能体 Web 和 Python 工具容器：

```powershell
docker compose up -d --force-recreate web python
```

打开 Web 看板：

```text
http://localhost:5000
```

如果页面没有变化，优先执行：

```powershell
docker compose up -d --force-recreate web python
```

因为 Flask 看板运行在容器里，切分支或改代码后需要重建容器才能加载当前文件。

## 8. 云端模型配置

当前 `agent` 分支已按 `aidawan.fun` 的 OpenAI 风格接口配置：

```env
LLM_API_KEY=你的 sk 开头令牌
LLM_BASE_URL=https://www.aidawan.fun/v1
LLM_MODEL=glm-5
LLM_TIMEOUT_SECONDS=60
```

项目实际请求地址为：

```text
POST https://www.aidawan.fun/v1/chat/completions
```

注意：

1. `LLM_BASE_URL` 只写到 `/v1`，代码会自动拼接 `/chat/completions`。
2. 当前已验证 `glm-5` 可以稳定生成项目报告。
3. `glm-5.1` 可以通过极简测试，但生成完整报告时可能被远端断开连接，因此不作为默认模型。
4. `gpt-5.4`、`gpt-5.5` 在测试时出现过 `503 Service temporarily unavailable`，不作为默认模型。
5. `.env` 不会提交到 GitHub，真实 API Key 只保存在你本地。

验证云端模型是否打通：

```powershell
@'
from career_insight.ai_module.llm_chatbot import CompatibleLLMClient
client = CompatibleLLMClient()
response = client.chat([{"role": "user", "content": "只回复 pong"}], temperature=0.1)
print(response.model)
print(response.used_fallback)
print(response.content)
'@ | docker compose exec -T -e PYTHONPATH=/workspace/src web python -
```

正常结果应包含：

```text
glm-5
False
pong
```

## 9. 运行智能体

### 9.1 在 Web 页面运行

1. 打开 `http://localhost:5000`。
2. 点击“运行智能体”。
3. 等待页面刷新。
4. 查看“最近运行”“步骤日志”“AI 分析报告”。

如果提示“智能体运行中”，说明后台线程还没结束，稍等后刷新即可。

### 9.2 在命令行运行

推荐用 Docker 容器运行：

```powershell
docker compose exec -T -e PYTHONPATH=/workspace/src python python -m career_insight.agent.cli
```

也可以使用脚本：

```powershell
.\scripts\bigdata-docker.cmd agent
```

成功时会输出 JSON，例如：

```json
{
  "run_id": 29,
  "status": "succeeded",
  "message": "流程智能体运行完成",
  "raw_count": 3,
  "clean_count": 3
}
```

重点看：

| 字段 | 正常含义 |
| --- | --- |
| `status` | `succeeded` 表示流程成功 |
| `message` | 只有“流程智能体运行完成”说明没有兜底警告 |
| `raw_count` | 原始岗位数量 |
| `clean_count` | 清洗后可分析岗位数量 |

如果 `message` 里出现“LLM 未配置或调用失败，已使用本地报告兜底”，说明 AI 报告没有走云端模型。

## 10. 数据采集配置

在 `.env` 里配置公开岗位页面：

```env
CRAWL_TARGET_URLS=https://sou.zhaopin.com/?kw=%E5%A4%A7%E6%95%B0%E6%8D%AE&kt=3
CRAWL_KEYWORDS=大数据,数据分析,Spark,Hive
CRAWL_MAX_PAGES=2
CRAWL_DELAY_SECONDS=3
```

说明：

1. `CRAWL_TARGET_URLS` 多个 URL 用英文逗号分隔。
2. 建议填写搜索结果页或具体岗位列表页，不要填写 `https://www.zhaopin.com/` 这类首页；首页能访问成功，但通常没有可解析的岗位列表。
3. 采集器只处理公开页面，不处理登录、验证码、付费内容或绕过反爬。
4. 如果 `CRAWL_TARGET_URLS` 留空，流程会直接分析 MySQL 中已有的 `raw_jobs` 数据。
5. 如果采集失败但数据库里已有数据，后续清洗和分析仍可继续。

## 11. MySQL 数据表说明

智能体相关数据主要存在 MySQL 的以下表中：

| 表名 | 作用 |
| --- | --- |
| `raw_jobs` | 原始岗位数据 |
| `agent_clean_jobs` | 清洗后的岗位数据 |
| `agent_runs` | 每次智能体运行记录 |
| `agent_run_steps` | 每次运行的步骤日志 |
| `agent_analysis_results` | 聚合分析结果 |
| `agent_reports` | AI 或本地兜底报告 |
| `agent_schedule` | 定时运行配置 |

如果你要向老师演示，可以重点讲：

1. `agent_runs` 证明智能体是多次可复现运行的。
2. `agent_run_steps` 证明每个步骤都有状态和日志。
3. `agent_reports` 证明分析结果被 AI 总结成报告。
4. `agent_clean_jobs` 证明数据经过了清洗，不是只展示原始文本。

## 12. HDFS 输出说明

智能体会尝试把结果同步到 HDFS。

如果 HDFS 同步失败，流程不会整体失败，而是把 `sync_hdfs` 标成 `warning`，继续生成报告。

原因是 HDFS 属于大数据链路展示的一部分，但 AI 报告不应该因为 HDFS 临时不可用而完全中断。

## 13. 看板接口

Flask 看板提供了几个本地 API：

| API | 方法 | 作用 |
| --- | --- | --- |
| `/` | GET | Web 看板页面 |
| `/api/dashboard` | GET | 获取看板全部状态 |
| `/api/agent/run` | POST | 手动启动智能体 |
| `/api/agent/status` | GET | 查看当前运行状态 |
| `/api/agent/report/latest` | GET | 查看最新报告 |
| `/api/agent/schedule` | POST | 更新每日定时运行配置 |

检查看板配置：

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:5000/api/dashboard
```

重点确认：

```json
{
  "llm_base_url": "https://www.aidawan.fun/v1",
  "llm_configured": true,
  "llm_model": "glm-5"
}
```

## 14. 常见问题处理

### 14.1 页面还是旧版本

原因：Docker 容器还在运行旧代码。

处理：

```powershell
docker compose up -d --force-recreate web python
```

### 14.2 AI 报告仍然兜底

先看 `.env`：

```env
LLM_API_KEY=必须有值
LLM_BASE_URL=https://www.aidawan.fun/v1
LLM_MODEL=glm-5
```

再重建容器：

```powershell
docker compose up -d --force-recreate web python
```

再跑最小模型测试：

```powershell
@'
from career_insight.ai_module.llm_chatbot import CompatibleLLMClient
client = CompatibleLLMClient()
response = client.chat([{"role": "user", "content": "只回复 pong"}])
print(response.content)
'@ | docker compose exec -T -e PYTHONPATH=/workspace/src web python -
```

### 14.3 `glm-5.1` 明明能 pong，为什么不用

测试时发现：

| 模型 | 极简 pong | 完整报告 |
| --- | --- | --- |
| `glm-5.1` | 成功 | 可能远端断开 |
| `glm-5` | 成功 | 成功 |
| `gpt-5.4` | 不稳定 | 可能 503 |
| `gpt-5.5` | 不稳定 | 可能 503 |

所以项目默认使用 `glm-5`。

### 14.4 端口 5000 打不开

检查容器：

```powershell
docker compose ps
```

看 Web 日志：

```powershell
docker logs zhitu-agent-web --tail 80
```

重启：

```powershell
docker compose up -d --force-recreate web
```

### 14.5 MySQL 连接失败

检查 MySQL 容器：

```powershell
docker compose ps mysql
docker logs zhitu-mysql --tail 80
```

如果 MySQL 未健康，先等一会儿再启动 Web：

```powershell
docker compose up -d mysql redis
docker compose up -d --force-recreate web python
```

## 15. 开发建议

在 `agent` 分支开发时建议遵守：

1. 不直接把实验改动放到 `main`。
2. 改完先跑 `python -m compileall src\career_insight`。
3. 改 Docker 配置后跑 `docker compose config --quiet`。
4. 改 AI 调用后至少跑一次 `pong` 测试。
5. 改流程后跑一次完整智能体 CLI。
6. 真实 API Key 只放 `.env`，不要写进 README 或代码。

## 16. 推荐验收清单

每次准备提交 `agent` 分支前，按下面检查：

```powershell
git status --short --branch
python -m compileall src\career_insight
docker compose config --quiet
docker compose up -d --force-recreate web python
docker compose exec -T -e PYTHONPATH=/workspace/src python python -m career_insight.agent.cli
```

然后打开：

```text
http://localhost:5000
```

确认：

1. 最近运行状态是 `succeeded`。
2. 运行消息没有“LLM 未配置或调用失败”。
3. 步骤日志完整。
4. 图表有数据。
5. AI 报告不是兜底模板。

## 17. 适合答辩时怎么讲

可以按这条线讲：

1. 原项目已经有 MySQL、HDFS、Hive、Spark 等大数据环境。
2. `agent` 分支把这些环节串成一个可执行流程智能体。
3. 智能体不是只调用 AI，而是先完成采集、清洗、分析和存储。
4. AI 的作用是把结构化分析指标转成可读的就业分析报告。
5. 即使云端模型失败，系统也有本地兜底，保证演示稳定。
6. Web 看板展示了运行记录、步骤日志、图表和报告，方便验收。

一句话总结：

```text
agent 分支是在大数据就业分析项目上增加的自动化流程智能体，它把数据采集、清洗、分析、HDFS 同步和 AI 报告生成串成了一个可复现的闭环。
```
