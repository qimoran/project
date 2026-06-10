from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import Flask, jsonify, request

from career_insight.agent.orchestrator import AgentRunner
from career_insight.agent.scheduler import DailyAgentScheduler
from career_insight.config.settings import as_text_list, get_settings
from career_insight.storage.mysql_handler import MySQLStore


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ", timespec="seconds") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def create_app() -> Flask:
    settings = get_settings()
    store = MySQLStore(settings)
    store.ensure_schema()
    if settings.agent_schedule_enabled:
        store.set_schedule(True, settings.agent_daily_time)

    runner = AgentRunner(settings)
    scheduler = DailyAgentScheduler(runner, store)
    scheduler.start()

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    @app.get("/")
    def index() -> str:
        return DASHBOARD_HTML

    @app.get("/api/dashboard")
    def dashboard():
        latest_run = store.latest_run()
        latest_report = store.latest_report()
        latest_steps = store.run_steps(latest_run["id"]) if latest_run else []
        analysis = store.latest_analysis()
        schedule = store.get_schedule()
        metrics = {}
        if latest_report and latest_report.get("metrics_json"):
            raw_metrics = latest_report["metrics_json"]
            if isinstance(raw_metrics, str):
                metrics = json.loads(raw_metrics)
            else:
                metrics = raw_metrics

        return jsonify(
            json_safe(
                {
                    "running": runner.is_running,
                    "settings": {
                        "mysql": settings.mysql_dsn_label,
                        "llm_configured": settings.llm_configured,
                        "llm_base_url": settings.llm_base_url,
                        "llm_model": settings.llm_model,
                        "crawl_target_urls": as_text_list(settings.crawl_target_urls),
                    },
                    "schedule": schedule,
                    "latest_run": latest_run,
                    "latest_steps": latest_steps,
                    "latest_report": latest_report,
                    "analysis": analysis,
                    "metrics": metrics,
                }
            )
        )

    @app.post("/api/agent/run")
    def run_agent():
        started = runner.start_background("manual")
        status_code = 202 if started else 409
        return jsonify({"started": started, "running": runner.is_running}), status_code

    @app.get("/api/agent/status")
    def agent_status():
        latest_run = store.latest_run()
        steps = store.run_steps(latest_run["id"]) if latest_run else []
        return jsonify(json_safe({"running": runner.is_running, "latest_run": latest_run, "steps": steps}))

    @app.get("/api/agent/report/latest")
    def latest_report():
        report = store.latest_report()
        return jsonify(json_safe({"report": report}))

    @app.post("/api/agent/schedule")
    def update_schedule():
        payload = request.get_json(silent=True) or {}
        enabled = bool(payload.get("enabled"))
        daily_time = str(payload.get("daily_time") or "09:00")
        if not re.match(r"^\d{2}:\d{2}$", daily_time):
            return jsonify({"error": "daily_time must use HH:MM format"}), 400
        hour, minute = [int(part) for part in daily_time.split(":")]
        if hour > 23 or minute > 59:
            return jsonify({"error": "daily_time is out of range"}), 400
        store.set_schedule(enabled, daily_time)
        return jsonify({"enabled": enabled, "daily_time": daily_time})

    return app


DASHBOARD_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>职途洞察流程智能体</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #20242c;
      --muted: #687080;
      --line: #dde2ea;
      --primary: #1f6feb;
      --success: #16833a;
      --warning: #a65f00;
      --danger: #c62828;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      background: #111827;
      color: white;
      padding: 22px 28px;
    }
    header h1 {
      margin: 0 0 6px;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0;
    }
    header p {
      margin: 0;
      color: #cbd5e1;
      font-size: 14px;
    }
    main {
      max-width: 1280px;
      margin: 0 auto;
      padding: 22px;
    }
    .toolbar, .grid, .charts {
      display: grid;
      gap: 14px;
    }
    .toolbar {
      grid-template-columns: 1fr auto auto;
      align-items: center;
      margin-bottom: 14px;
    }
    .status-line {
      color: var(--muted);
      font-size: 14px;
    }
    button {
      border: 1px solid var(--primary);
      border-radius: 6px;
      background: var(--primary);
      color: white;
      height: 38px;
      padding: 0 14px;
      font-size: 14px;
      cursor: pointer;
    }
    button.secondary {
      background: white;
      color: var(--primary);
    }
    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
    .grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-bottom: 14px;
    }
    .charts {
      grid-template-columns: 1fr 1fr;
      margin-bottom: 14px;
    }
    section, .metric {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    .metric strong {
      display: block;
      font-size: 26px;
      line-height: 1.2;
    }
    .metric span {
      color: var(--muted);
      font-size: 13px;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 17px;
    }
    .chart {
      width: 100%;
      height: 320px;
    }
    .report {
      white-space: pre-wrap;
      line-height: 1.68;
      font-size: 15px;
    }
    .steps {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    .steps th, .steps td {
      border-bottom: 1px solid var(--line);
      padding: 9px;
      text-align: left;
      vertical-align: top;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border-radius: 999px;
      background: #eef2ff;
      color: #243b76;
      font-size: 12px;
    }
    .succeeded { color: var(--success); }
    .warning { color: var(--warning); }
    .failed { color: var(--danger); }
    .running { color: var(--primary); }
    .schedule {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 13px;
    }
    input[type="time"] {
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 8px;
    }
    @media (max-width: 900px) {
      .toolbar, .grid, .charts {
        grid-template-columns: 1fr;
      }
      main { padding: 14px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>职途洞察流程智能体</h1>
    <p>采集、清洗、分析、AI 报告生成和网页展示的一体化控制台</p>
  </header>
  <main>
    <div class="toolbar">
      <div class="status-line" id="statusLine">正在加载状态...</div>
      <button id="runButton" type="button">运行智能体</button>
      <button class="secondary" id="refreshButton" type="button">刷新</button>
    </div>

    <section style="margin-bottom:14px">
      <h2>定时调度</h2>
      <div class="schedule">
        <label><input type="checkbox" id="scheduleEnabled"> 启用每天自动运行</label>
        <input type="time" id="scheduleTime" value="09:00">
        <button class="secondary" id="saveScheduleButton" type="button">保存调度</button>
        <span id="scheduleTip"></span>
      </div>
    </section>

    <div class="grid">
      <div class="metric"><strong id="totalJobs">0</strong><span>分析岗位数</span></div>
      <div class="metric"><strong id="avgSalary">-</strong><span>平均薪资 K/月</span></div>
      <div class="metric"><strong id="cityCount">0</strong><span>覆盖城市</span></div>
      <div class="metric"><strong id="skillCount">0</strong><span>识别技能</span></div>
    </div>

    <div class="charts">
      <section>
        <h2>城市薪资</h2>
        <div id="cityChart" class="chart"></div>
      </section>
      <section>
        <h2>技能热度</h2>
        <div id="skillChart" class="chart"></div>
      </section>
    </div>

    <section style="margin-bottom:14px">
      <h2>运行步骤</h2>
      <table class="steps">
        <thead>
          <tr><th>步骤</th><th>状态</th><th>说明</th><th>完成时间</th></tr>
        </thead>
        <tbody id="stepsBody"></tbody>
      </table>
    </section>

    <section>
      <h2>AI 分析报告</h2>
      <div class="report" id="reportBox">暂无报告，点击“运行智能体”生成。</div>
    </section>
  </main>

  <script>
    const cityChart = echarts.init(document.getElementById("cityChart"));
    const skillChart = echarts.init(document.getElementById("skillChart"));
    const runButton = document.getElementById("runButton");
    const refreshButton = document.getElementById("refreshButton");
    const saveScheduleButton = document.getElementById("saveScheduleButton");

    function formatStatus(run, running) {
      if (running) return "智能体正在运行...";
      if (!run) return "还没有运行记录";
      return `最近运行 #${run.id}：${run.status}，${run.message || ""}`;
    }

    function renderCharts(data) {
      const cityRows = data.analysis.city_salary || [];
      cityChart.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: 46, right: 20, top: 28, bottom: 50 },
        xAxis: { type: "category", data: cityRows.map(row => row.city) },
        yAxis: { type: "value", name: "K/月" },
        series: [{ type: "bar", data: cityRows.map(row => row.avg_salary || 0), itemStyle: { color: "#1f6feb" } }]
      });

      const skillRows = data.analysis.skill_hotness || [];
      skillChart.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: 46, right: 20, top: 28, bottom: 50 },
        xAxis: { type: "category", data: skillRows.slice(0, 10).map(row => row.skill) },
        yAxis: { type: "value", name: "岗位数" },
        series: [{ type: "bar", data: skillRows.slice(0, 10).map(row => row.job_count), itemStyle: { color: "#16a34a" } }]
      });
    }

    function renderSteps(steps) {
      const body = document.getElementById("stepsBody");
      body.innerHTML = "";
      if (!steps || steps.length === 0) {
        body.innerHTML = '<tr><td colspan="4">暂无步骤记录</td></tr>';
        return;
      }
      for (const step of steps) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${step.step_name}</td>
          <td class="${step.status}">${step.status}</td>
          <td>${step.detail || ""}</td>
          <td>${step.finished_at || ""}</td>
        `;
        body.appendChild(tr);
      }
    }

    async function loadDashboard() {
      const response = await fetch("/api/dashboard");
      const data = await response.json();
      document.getElementById("statusLine").textContent = formatStatus(data.latest_run, data.running);
      runButton.disabled = data.running;
      document.getElementById("totalJobs").textContent = data.metrics.total_jobs || 0;
      document.getElementById("avgSalary").textContent = data.metrics.avg_salary || "-";
      document.getElementById("cityCount").textContent = (data.analysis.city_salary || []).length;
      document.getElementById("skillCount").textContent = (data.analysis.skill_hotness || []).length;
      document.getElementById("scheduleEnabled").checked = Boolean(data.schedule.enabled);
      document.getElementById("scheduleTime").value = data.schedule.daily_time || "09:00";

      const report = data.latest_report && data.latest_report.report_markdown;
      document.getElementById("reportBox").textContent = report || "暂无报告，点击“运行智能体”生成。";
      renderCharts(data);
      renderSteps(data.latest_steps || []);
    }

    runButton.addEventListener("click", async () => {
      runButton.disabled = true;
      await fetch("/api/agent/run", { method: "POST" });
      await loadDashboard();
    });

    refreshButton.addEventListener("click", loadDashboard);

    saveScheduleButton.addEventListener("click", async () => {
      const enabled = document.getElementById("scheduleEnabled").checked;
      const daily_time = document.getElementById("scheduleTime").value || "09:00";
      const response = await fetch("/api/agent/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled, daily_time })
      });
      document.getElementById("scheduleTip").textContent = response.ok ? "已保存" : "保存失败";
      await loadDashboard();
    });

    window.addEventListener("resize", () => {
      cityChart.resize();
      skillChart.resize();
    });

    loadDashboard();
    setInterval(loadDashboard, 10000);
  </script>
</body>
</html>
"""


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
