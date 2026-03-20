from __future__ import annotations

import argparse
import asyncio
import uuid
import json
from datetime import datetime
from pathlib import Path

from config import settings
from graph.workflow import (
    build_run_config,
    create_async_sqlite_checkpointer,
    create_scraping_graph,
)


async def run_standalone_task(task: str, task_type: str = "auto") -> None:
    """
    Run a crawler task locally without MCP.
    """
    print(f"[START] task={task}")
    print(f"[TYPE] task_type={task_type}")

    thread_id = str(uuid.uuid4())
    task_id = f"local_{thread_id[:8]}"
    config = build_run_config(thread_id)

    initial_state = {
        "task_description": task,
        "task_type": task_type,
        "urls": [],
        "max_steps": settings.DEFAULT_MAX_PAGES,
        "step_count": 0,
        "extracted_data": [],
        "error_count": 0,
        "screenshot_history": [],
        "visited_urls": [],
        "metadata": {
            "task_id": task_id,
            "thread_id": thread_id,
            "runtime": "standalone",
        },
    }

    try:
        async with create_async_sqlite_checkpointer(
            settings.checkpoint_db_path.as_posix()
        ) as checkpointer:
            app = create_scraping_graph(checkpointer=checkpointer)

            async for event in app.astream(initial_state, config=config):
                for node_name, state_update in event.items():
                    print(f"[NODE] {node_name} done")
                    if node_name == "browser":
                        browser_content = str(
                            state_update.get("current_page_content", "") or ""
                        )
                        if browser_content:
                            print("[BROWSER_CONTENT_START]")
                            print(browser_content[:4000])
                            if len(browser_content) > 4000:
                                print(
                                    f"...(truncated, total={len(browser_content)} chars)"
                                )
                            print("[BROWSER_CONTENT_END]")
                    if "analysis_report" in state_update:
                        summary = str(state_update["analysis_report"])
                        preview = summary[:100] + ("..." if len(summary) > 100 else "")
                        print(f"[SUMMARY] {preview}")

            final_state = await app.aget_state(config)
            extracted = final_state.values.get("extracted_data", [])
            analysis_report = str(final_state.values.get("analysis_report", "") or "")
            browser_content_final = str(
                final_state.values.get("current_page_content", "") or ""
            )
            status = str(final_state.values.get("next_step", "end"))

            reports_dir = settings.BASE_DIR / "outputs" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = f"{ts}_{task_id}"
            md_path = reports_dir / f"{stem}.md"
            json_path = reports_dir / f"{stem}.json"
            browser_txt_path = reports_dir / f"{stem}_browser_content.txt"

            md_content = (
                f"# Crawl Report\n\n"
                f"- task_id: `{task_id}`\n"
                f"- thread_id: `{thread_id}`\n"
                f"- task_type: `{task_type}`\n"
                f"- status: `{status}`\n"
                f"- extracted_count: `{len(extracted)}`\n\n"
                f"## Task\n\n{task}\n\n"
                f"## Browser Raw Content\n\n"
                f"Saved to `{browser_txt_path.name}` (length={len(browser_content_final)} chars)\n\n"
                f"## Analysis Report\n\n{analysis_report or 'No report generated.'}\n"
            )
            md_path.write_text(md_content, encoding="utf-8")
            json_path.write_text(
                json.dumps(final_state.values, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            browser_txt_path.write_text(browser_content_final, encoding="utf-8")

            print("[DONE] task completed")
            print(f"[RESULT] extracted_count={len(extracted)}")
            print(f"[REPORT] markdown={md_path}")
            print(f"[REPORT] json={json_path}")
            print(f"[REPORT] browser_content={browser_txt_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAILED] {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run standalone crawler task.")
    parser.add_argument("--task", required=True, help="Crawler task description.")
    parser.add_argument(
        "--task-type",
        default="auto",
        help="Analyst routing type: auto/general/competitor/financial",
    )
    args = parser.parse_args()
    asyncio.run(run_standalone_task(args.task, task_type=args.task_type))
