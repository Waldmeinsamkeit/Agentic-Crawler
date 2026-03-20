from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from config import settings
from graph.workflow import (
    build_run_config,
    create_async_sqlite_checkpointer,
    create_scraping_graph,
)
from utils.db_handler import DBHandler

mcp = FastMCP(settings.MCP_SERVER_NAME)

report_db = DBHandler(settings.reports_db_path)


def _make_task_id() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"task_{ts}_{uuid.uuid4().hex[:8]}"


def _make_thread_id(task_id: str) -> str:
    return f"{settings.THREAD_PREFIX}_{task_id}"


@mcp.tool()
async def run_crawler_task(
    task_description: str,
    max_pages: int = 3,
    analysis_type: str = "general",
    task_id: str | None = None,
    thread_id: str | None = None,
    urls: list[str] | None = None,
) -> str:
    """
    Run an AI crawler task and return a report.
    Reuse the same thread_id to resume from checkpoint.
    """
    resolved_task_id = task_id or _make_task_id()
    resolved_thread_id = thread_id or _make_thread_id(resolved_task_id)
    max_steps = max(1, min(20, max_pages or settings.DEFAULT_MAX_PAGES))

    initial_state: dict[str, Any] = {
        "task_description": task_description,
        "task_type": analysis_type,
        "urls": urls or [],
        "max_steps": max_steps,
        "step_count": 0,
        "extracted_data": [],
        "error_count": 0,
        "screenshot_history": [],
        "visited_urls": [],
        "metadata": {
            "task_id": resolved_task_id,
            "thread_id": resolved_thread_id,
        },
    }

    config = build_run_config(resolved_thread_id)
    try:
        async with create_async_sqlite_checkpointer(
            settings.checkpoint_db_path.as_posix()
        ) as checkpointer:
            scraping_graph = create_scraping_graph(
                checkpointer=checkpointer,
                interrupt_before=["browser_node"]
                if settings.INTERRUPT_BEFORE_BROWSER
                else None,
            )
            final_state = await scraping_graph.ainvoke(initial_state, config=config)
        status = "completed"
        if final_state.get("requires_human_input"):
            status = "paused_for_human"
        elif final_state.get("next_step") == "retry":
            status = "failed_retry_needed"

        report_db.upsert_task_report(
            task_id=resolved_task_id,
            thread_id=resolved_thread_id,
            task_description=task_description,
            analysis_type=analysis_type,
            status=status,
            analysis_report=final_state.get("analysis_report", ""),
            extracted_data=final_state.get("extracted_data", []),
            error_count=int(final_state.get("error_count", 0)),
        )

        return (
            "### Crawl Report\n\n"
            f"- task_id: {resolved_task_id}\n"
            f"- thread_id: {resolved_thread_id}\n"
            f"- status: {status}\n\n"
            f"{final_state.get('analysis_report', 'No report generated')}"
        )
    except Exception as exc:  # noqa: BLE001
        report_db.upsert_task_report(
            task_id=resolved_task_id,
            thread_id=resolved_thread_id,
            task_description=task_description,
            analysis_type=analysis_type,
            status="failed",
            analysis_report=f"Task failed: {exc}",
            extracted_data=[],
            error_count=1,
        )
        return (
            "Task failed\n\n"
            f"- task_id: {resolved_task_id}\n"
            f"- thread_id: {resolved_thread_id}\n"
            f"- error: {exc}"
        )


@mcp.resource("reports://{task_id}")
async def get_task_report(task_id: str) -> str:
    """Read historical report by task id."""
    row = report_db.get_task_report(task_id)
    items = report_db.get_reports_by_task(task_id)
    if not row and not items:
        return f"No report found for task: {task_id}"

    header = ""
    if row:
        header = (
            f"### Historical Report\n\n"
            f"- task_id: {row.task_id}\n"
            f"- thread_id: {row.thread_id}\n"
            f"- status: {row.status}\n"
            f"- updated_at: {row.updated_at}\n\n"
            f"#### Analysis\n{row.analysis_report}\n\n"
            f"#### Structured JSON\n{row.extracted_data_json}\n\n"
        )

    intelligence_block = "#### Intelligence Rows\n"
    if not items:
        intelligence_block += "- no intelligence rows yet"
    else:
        lines = []
        for item in items[:10]:
            lines.append(
                f"- [{item.created_at}] {item.category} | url={item.source_url} | summary={item.summary[:120]}"
            )
        intelligence_block += "\n".join(lines)
    return header + intelligence_block


if __name__ == "__main__":
    mcp.run()
