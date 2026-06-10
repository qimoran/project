# 职途洞察核心代码包

`career_insight` 是项目的业务代码包，当前重点包含流程智能体能力：

```text
crawlers              公开招聘页面慢速采集
data_processing       岗位字段清洗、薪资解析、技能归一化
analysis              城市薪资、技能热度、学历/经验分布
storage               MySQL 和 HDFS 读写
ai_module             OpenAI-compatible 云端模型报告生成
agent                 受控流程智能体编排和定时调度
visualization         Flask 网页看板和 API
```

命令行运行一次智能体：

```bash
PYTHONPATH=/workspace/src python -m career_insight.agent.cli
```

启动网页看板：

```bash
PYTHONPATH=/workspace/src python -m career_insight.visualization.app
```

Docker 环境中推荐使用项目根目录脚本：

```powershell
.\scripts\bigdata-docker.cmd web
.\scripts\bigdata-docker.cmd agent
```
