from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable

from career_insight.ai_module.recommendation import generate_ai_report
from career_insight.analysis.salary_analysis import run_salary_and_trend_analysis
from career_insight.config.settings import Settings, get_settings
from career_insight.crawlers.selenium_scraper import SlowJobScraper
from career_insight.data_processing.cleaner import clean_jobs
from career_insight.storage.hdfs_handler import sync_agent_outputs
from career_insight.storage.mysql_handler import MySQLStore


@dataclass
class AgentRunResult:
    run_id: int
    status: str
    message: str
    raw_count: int
    clean_count: int
    metrics: dict[str, Any]


class WorkflowAgent:
    def __init__(
        self,
        settings: Settings | None = None,
        store: MySQLStore | None = None,
        scraper_factory: Callable[[], SlowJobScraper] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.store = store or MySQLStore(self.settings)
        self.scraper_factory = scraper_factory or (lambda: SlowJobScraper(self.settings))

    def run(self, trigger_type: str = "manual") -> AgentRunResult:
        self.store.ensure_schema()
        run_id = self.store.create_run(trigger_type)
        raw_count = 0
        clean_count = 0
        metrics: dict[str, Any] = {}
        warnings: list[str] = []

        try:
            step_id = self.store.start_step(run_id, "crawl_jobs", "慢速采集配置的公开岗位页面")
            crawl_result = self.scraper_factory().crawl()
            inserted = self.store.insert_raw_jobs(crawl_result.jobs)
            raw_rows = self.store.fetch_raw_jobs()
            raw_count = len(raw_rows)
            detail = (
                f"访问 {len(crawl_result.visited_urls)} 个页面，解析 {len(crawl_result.jobs)} 条，"
                f"写入/更新 {inserted} 条，当前 raw_jobs 共 {raw_count} 条"
            )
            if crawl_result.errors:
                warnings.extend(crawl_result.errors)
                detail += "；部分页面失败：" + " | ".join(crawl_result.errors[:3])
            if not self.settings.crawl_target_urls:
                detail += "；未配置 CRAWL_TARGET_URLS，本次直接分析已有 raw_jobs 数据"
            self.store.finish_step(step_id, "succeeded", detail)

            step_id = self.store.start_step(run_id, "clean_jobs", "标准化岗位、薪资、技能和城市字段")
            cleaned = clean_jobs(raw_rows)
            clean_count = self.store.replace_clean_jobs(cleaned)
            if clean_count == 0:
                raise RuntimeError("没有可分析的岗位数据，请先配置真实采集 URL 或导入 raw_jobs")
            self.store.finish_step(step_id, "succeeded", f"生成 agent_clean_jobs {clean_count} 条")

            step_id = self.store.start_step(run_id, "run_analysis", "聚合城市薪资、技能、学历和经验分布")
            metrics = run_salary_and_trend_analysis(run_id, cleaned, self.store)
            self.store.finish_step(
                step_id,
                "succeeded",
                f"分析完成：{metrics.get('total_jobs', 0)} 条岗位，"
                f"{len(metrics.get('city_salary', []))} 个城市，"
                f"{len(metrics.get('skill_hotness', []))} 个技能",
            )

            step_id = self.store.start_step(run_id, "sync_hdfs", "同步清洗数据和指标到 HDFS")
            try:
                written = sync_agent_outputs(run_id, jobs=cleaned, metrics=metrics, settings=self.settings)
                self.store.finish_step(step_id, "succeeded", "写入：" + ", ".join(written))
            except Exception as exc:
                warnings.append(f"HDFS 同步失败：{exc}")
                self.store.finish_step(step_id, "warning", f"HDFS 同步失败，不影响报告生成：{exc}")

            step_id = self.store.start_step(run_id, "generate_ai_report", "调用云端兼容模型生成报告")
            report = generate_ai_report(metrics)
            title = "招聘数据智能分析报告"
            if report.used_fallback:
                warnings.append(report.fallback_reason or "LLM 报告使用本地规则兜底")
            self.store.save_report(
                run_id,
                title=title,
                report_markdown=report.content,
                metrics=metrics,
                llm_model=report.model,
            )
            self.store.finish_step(
                step_id,
                "succeeded" if not report.used_fallback else "warning",
                (
                    f"报告已生成，模型：{report.model}"
                    if not report.used_fallback
                    else f"报告已使用本地规则兜底；{report.fallback_reason}"
                ),
            )

            message = "流程智能体运行完成"
            if warnings:
                message += "；提示：" + " | ".join(warnings[:3])
            self.store.finish_run(
                run_id,
                status="succeeded",
                message=message,
                raw_count=raw_count,
                clean_count=clean_count,
            )
            return AgentRunResult(run_id, "succeeded", message, raw_count, clean_count, metrics)
        except Exception as exc:
            message = f"流程智能体运行失败：{exc}"
            self.store.finish_run(
                run_id,
                status="failed",
                message=message,
                raw_count=raw_count,
                clean_count=clean_count,
            )
            return AgentRunResult(run_id, "failed", message, raw_count, clean_count, metrics)


class AgentRunner:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._last_result: AgentRunResult | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_result(self) -> AgentRunResult | None:
        return self._last_result

    def start_background(self, trigger_type: str = "manual") -> bool:
        if self.is_running:
            return False
        self._thread = threading.Thread(
            target=self._run_locked,
            args=(trigger_type,),
            daemon=True,
            name="career-insight-agent",
        )
        self._thread.start()
        return True

    def run_sync(self, trigger_type: str = "manual") -> AgentRunResult:
        with self._lock:
            self._last_result = WorkflowAgent(self.settings).run(trigger_type)
            return self._last_result

    def _run_locked(self, trigger_type: str) -> None:
        with self._lock:
            self._last_result = WorkflowAgent(self.settings).run(trigger_type)
