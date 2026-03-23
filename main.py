from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path

from config import settings
from graph.workflow import (
    build_run_config,
    create_async_sqlite_checkpointer,
    create_full_graph,
)
from utils.logger import (
    add_task_file_handler,
    logger,
    remove_task_file_handler,
    reset_task_context,
    set_task_context,
)


async def run_standalone_daily_command(daily_command: str, task_type: str = "auto") -> None:
    """
    Run supervisor-driven daily command locally (no MCP).
    Supervisor decomposes command, dispatches worker tasks in parallel, then summarizes.
    """
    thread_id = str(uuid.uuid4())
    task_id = f"daily_{thread_id[:8]}"
    token = set_task_context(thread_id)
    log_path = add_task_file_handler(thread_id)
    logger.info("Start daily command: %s", daily_command)
    logger.info("Task type: %s", task_type)
    logger.info("Task log file: %s", log_path)

    config = build_run_config(thread_id)
    initial_state = {
        "task_description": daily_command,
        "task_type": task_type,
        "metadata": {
            "task_id": task_id,
            "thread_id": thread_id,
            "runtime": "standalone_supervisor",
        },
        "worker_outputs": [],
        "extracted_data": [],
    }

    try:
        async with create_async_sqlite_checkpointer(
            settings.checkpoint_db_path.as_posix()
        ) as checkpointer:
            app = create_full_graph(checkpointer=checkpointer)

            async for event in app.astream(initial_state, config=config):
                for node_name, state_update in event.items():
                    logger.info("Node finished: %s", node_name)
                    if node_name == "supervisor_plan":
                        logger.info("Plan summary: %s", state_update.get("plan_summary", ""))
                        logger.info(
                            "Subtasks count: %s",
                            len(state_update.get("sub_tasks", []) or []),
                        )
                    if node_name == "browser_worker":
                        outputs = state_update.get("worker_outputs", []) or []
                        if outputs:
                            item = outputs[-1]
                            logger.info(
                                "Worker output: sub_task_id=%s url=%s",
                                item.get("sub_task_id"),
                                item.get("target_url"),
                            )
                    if "analysis_report" in state_update:
                        logger.info("Daily report preview: %s", str(state_update["analysis_report"])[:200])

            final_state = await app.aget_state(config)
            final_values = dict(final_state.values)
            analysis_report = str(final_values.get("analysis_report", "") or "")
            worker_outputs = list(final_values.get("worker_outputs", []) or [])
            extracted = list(final_values.get("extracted_data", []) or [])
            status = str(final_values.get("next_step", "end"))

            reports_dir = settings.BASE_DIR / "outputs" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = f"{ts}_{task_id}"
            md_path = reports_dir / f"{stem}.md"
            json_path = reports_dir / f"{stem}.json"
            workers_json_path = reports_dir / f"{stem}_workers.json"

            md_content = (
                f"# Daily Intelligence Report\n\n"
                f"- task_id: `{task_id}`\n"
                f"- thread_id: `{thread_id}`\n"
                f"- task_type: `{task_type}`\n"
                f"- status: `{status}`\n"
                f"- worker_outputs: `{len(worker_outputs)}`\n"
                f"- extracted_count: `{len(extracted)}`\n\n"
                f"## Daily Command\n\n{daily_command}\n\n"
                f"## Final Report\n\n{analysis_report or 'No report generated.'}\n"
            )
            md_path.write_text(md_content, encoding="utf-8")
            json_path.write_text(
                json.dumps(final_values, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            workers_json_path.write_text(
                json.dumps(worker_outputs, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

            logger.info("Daily command completed")
            logger.info("Worker outputs: %s", len(worker_outputs))
            logger.info("Extracted count: %s", len(extracted))
            logger.info("Report markdown: %s", md_path)
            logger.info("Report json: %s", json_path)
            logger.info("Workers json: %s", workers_json_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Daily command failed: %s", exc)
    finally:
        remove_task_file_handler(thread_id)
        reset_task_context(token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run supervisor-driven daily command.")
    parser.add_argument("--command", required=True, help="Daily command for supervisor to decompose.")
    parser.add_argument(
        "--task-type",
        default="auto",
        help="Analyst routing type: auto/general/competitor/financial",
    )
    args = parser.parse_args()
    asyncio.run(run_standalone_daily_command(args.command, task_type=args.task_type))

