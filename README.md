# 项目名称
职途洞察
# 项目背景

我是大学本科大数据专业大三的学生，我现在要做一个实践项目，项目时长是四周全天，基于大数据平台对智联招聘网站的招聘数据进行爬取，处理，存储，分析，可视化展示。

# 项目功能
1. 数据爬取：使用Python的爬虫库（如Scrapy或BeautifulSoup）从智联招聘网站上爬取招聘信息，包括职位名称、公司名称、工作地点、薪资待遇、职位要求等。
2. 数据处理：对爬取到的数据进行清洗和预处理，包括去除重复数据、处理缺失值、标准化数据格式等。
3. 数据存储：将处理后的数据存储到数据库中（如MySQL或MongoDB），以便后续的分析和查询。
4. 数据分析：使用数据分析工具（如Pandas、NumPy）对存储的数据进行分析，挖掘招聘市场的趋势和规律，例如热门职位、薪资水平、地区分布等。
5. 可视化展示：使用数据可视化工具echarts将分析结果以图表的形式展示出来，帮助用户更直观地理解招聘市场的情况。
# 项目技术栈
- 编程语言：Python = 3.12
- 爬虫库：Scrapy或BeautifulSoup
- 数据处理库：Pandas、NumPy
- 数据库：MySQL 8.0 redis 5.0.14
- 数据可视化工具：echarts
- 大数据平台：Hadoop3.3.6 hive 4.0.1 Spark3.5.1,
# 项目目标

# 项目启动与关闭

启动完整大数据环境：

```powershell
.\scripts\bigdata-docker.cmd up-all
```

查看容器状态：

```powershell
.\scripts\bigdata-docker.cmd status
```

关闭项目：

```powershell
.\scripts\bigdata-docker.cmd down
```

# AI 流程智能体

`agent` 分支加入了“流程智能体”：

```text
公开招聘页面慢速采集 -> raw_jobs -> agent_clean_jobs -> 分析表 -> HDFS -> AI 报告 -> Web 看板
```

启动网页看板：

```powershell
.\scripts\bigdata-docker.cmd web
```

浏览器打开：

```text
http://localhost:5000
```

手动在容器里跑一次智能体：

```powershell
.\scripts\bigdata-docker.cmd agent
```

云端模型配置在 `.env`：

```env
LLM_API_KEY=
LLM_BASE_URL=https://www.aidawan.fun/v1
LLM_MODEL=glm-5
```

项目会调用 OpenAI 风格的 `/v1/chat/completions`，当前已验证 `glm-5` 可以稳定生成报告。

`LLM_API_KEY` 留空时，系统不会报错，会使用本地规则生成一份兜底报告。要采集真实公开页面，把页面 URL 填到：

```env
CRAWL_TARGET_URLS=
```

多个 URL 用英文逗号分隔。采集器只做公开页面慢速抓取，不处理登录、验证码或绕过反爬。
