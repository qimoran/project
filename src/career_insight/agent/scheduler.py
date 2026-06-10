from __future__ import annotations

import threading
import time
from datetime import datetime

from career_insight.agent.orchestrator import AgentRunner
from career_insight.storage.mysql_handler import MySQLStore


class DailyAgentScheduler:
    def __init__(self, runner: AgentRunner, store: MySQLStore) -> None:
        self.runner = runner
        self.store = store
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_run_key = ""

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="career-insight-agent-scheduler",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                pass
            self._stop.wait(30)

    def _tick(self) -> None:
        schedule = self.store.get_schedule()
        if not schedule.get("enabled"):
            return
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        run_key = now.strftime("%Y-%m-%d") + " " + current_time
        if current_time != schedule.get("daily_time"):
            return
        if self._last_run_key == run_key:
            return
        if self.runner.start_background("schedule"):
            self._last_run_key = run_key
