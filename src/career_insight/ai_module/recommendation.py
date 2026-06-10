from __future__ import annotations

import json
from typing import Any

from career_insight.ai_module.llm_chatbot import CompatibleLLMClient, LLMResponse


def build_report_prompt(metrics: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是一个大数据就业分析助手。请基于结构化招聘分析数据，"
                "输出适合本科大数据实践项目答辩展示的中文 Markdown 报告。"
                "报告要具体、克制，不能编造数据。"
            ),
        },
        {
            "role": "user",
            "content": (
                "请根据下面 JSON 指标生成报告，包含："
                "1. 总体结论；2. 城市薪资观察；3. 热门技能；"
                "4. 学历和经验要求；5. 给大三学生的学习建议；"
                "6. 下一步数据采集/分析建议。\n\n"
                f"指标 JSON：\n{json.dumps(metrics, ensure_ascii=False, default=str)}"
            ),
        },
    ]


def fallback_report(metrics: dict[str, Any], reason: str = "") -> str:
    total = metrics.get("total_jobs", 0)
    avg_salary = metrics.get("avg_salary")
    city_salary = metrics.get("city_salary", [])
    skills = metrics.get("skill_hotness", [])
    education = metrics.get("education_distribution", [])
    experience = metrics.get("experience_distribution", [])

    top_city = city_salary[0] if city_salary else None
    top_skills = "、".join(item["skill"] for item in skills[:5]) if skills else "暂无"
    top_education = education[0]["education"] if education else "暂无"
    top_experience = experience[0]["experience"] if experience else "暂无"
    reason_text = f"\n\n> 说明：{reason}" if reason else ""

    return f"""# 招聘数据智能分析报告

## 总体结论

本次流程智能体共分析 {total} 条岗位数据，整体平均薪资为 {avg_salary or "暂无"} K/月。{
        "薪资最高或最有代表性的城市是 " + top_city["city"] + "，平均薪资约 " + str(top_city["avg_salary"]) + " K/月。" if top_city else "当前城市薪资数据不足。"
    }

## 城市薪资观察

{_markdown_table(city_salary[:8], ["city", "job_count", "avg_salary"], ["城市", "岗位数", "平均薪资K/月"])}

## 热门技能

当前样本中出现较多的技能是：{top_skills}。建议优先把 Python、SQL、Spark、Hive、数据清洗和可视化串成可演示项目链路。

## 学历和经验要求

- 最常见学历要求：{top_education}
- 最常见经验要求：{top_experience}

## 学习建议

1. 先保证 MySQL、HDFS、Hive、Spark 的数据链路稳定可复现。
2. 用真实岗位数据沉淀技能词频和薪资趋势，避免只展示模拟数据。
3. 把分析结果接入网页看板，用 AI 总结说明“数据说明了什么”和“下一步怎么做”。

## 下一步建议

继续扩大采集城市和关键词范围，并记录每次采集数量、清洗数量、失败原因和分析结果变化。{reason_text}
"""


def generate_ai_report(metrics: dict[str, Any], client: CompatibleLLMClient | None = None) -> LLMResponse:
    llm = client or CompatibleLLMClient()
    try:
        response = llm.chat(build_report_prompt(metrics))
        if response.used_fallback or not response.content.strip():
            reason = response.fallback_reason or "未配置 LLM_API_KEY，已使用本地规则生成报告。"
            return LLMResponse(
                content=fallback_report(metrics, reason),
                model=response.model,
                used_fallback=True,
                fallback_reason=reason,
            )
        return response
    except Exception as exc:
        reason = f"云端模型调用失败：{exc}"
        return LLMResponse(
            content=fallback_report(metrics, reason),
            model=llm.settings.llm_model,
            used_fallback=True,
            fallback_reason=reason,
        )


def _markdown_table(rows: list[dict[str, Any]], keys: list[str], labels: list[str]) -> str:
    if not rows:
        return "暂无数据"
    header = "| " + " | ".join(labels) + " |"
    separator = "| " + " | ".join(["---"] * len(keys)) + " |"
    body = [
        "| " + " | ".join(str(row.get(key, "")) for key in keys) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])
