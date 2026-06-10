from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import Flask, jsonify, render_template, request

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
        return render_template("dashboard.html")

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


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
