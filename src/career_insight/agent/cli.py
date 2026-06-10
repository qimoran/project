from __future__ import annotations

import argparse
import json
import sys

from career_insight.agent.orchestrator import WorkflowAgent
from career_insight.config.settings import get_settings
from career_insight.storage.mysql_handler import MySQLStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Career Insight workflow agent.")
    parser.add_argument("--init-db", action="store_true", help="Only create agent tables.")
    parser.add_argument("--trigger", default="cli", help="Trigger label written to agent_runs.")
    args = parser.parse_args()

    settings = get_settings()
    store = MySQLStore(settings)
    store.ensure_schema()
    if args.init_db:
        print("Agent tables are ready.")
        return 0

    result = WorkflowAgent(settings, store).run(args.trigger)
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "status": result.status,
                "message": result.message,
                "raw_count": result.raw_count,
                "clean_count": result.clean_count,
                "metrics": result.metrics,
            },
            ensure_ascii=False,
            default=str,
            indent=2,
        )
    )
    return 0 if result.status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
