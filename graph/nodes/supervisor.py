from __future__ import annotations

import inspect
from typing import Any

from langchain_core.runnables.config import RunnableConfig

from agents.runners import default_analyst_runner, default_browser_runner
from agents.supervisor import SupervisorAgent, TaskPlan
from graph.state import AgentState
from utils.model_factory import ModelFactory


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def supervisor_plan_node(state: AgentState) -> dict[str, Any]:
    llm = ModelFactory.get_model(scene=ModelFactory.SCENE_GENERAL)
    try:
        fallback_llm = ModelFactory.get_fallback_model(scene=ModelFactory.SCENE_GENERAL)
    except Exception:  # noqa: BLE001
        fallback_llm = None

    supervisor = SupervisorAgent(model=llm, fallback_model=fallback_llm)
    daily_command = state.get("task_description", "")
    plan = await supervisor.create_plan(daily_command)
    plan = plan if isinstance(plan, TaskPlan) else TaskPlan.model_validate(plan)

    tasks = [task.model_dump() for task in plan.tasks]
    return {
        "plan_summary": plan.plan_summary,
        "task_plan": plan.model_dump(),
        "sub_tasks": tasks,
        "worker_outputs": [],
    }


async def browser_worker_node(
    state: AgentState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    thread_id = str((config or {}).get("configurable", {}).get("thread_id", "default_user"))
    target_url = str(state.get("target_url", "") or "")
    task_goal = str(state.get("task_goal", state.get("task_description", "")) or "")
    task_id = int(state.get("id", 0) or 0)
    priority = int(state.get("priority", 1) or 1)

    browser_task = task_goal
    if target_url:
        browser_task = f"{task_goal}\nTarget URL: {target_url}"

    browser_result = await _maybe_await(
        default_browser_runner(
            task_description=browser_task,
            urls=[target_url] if target_url else [],
            thread_id=f"{thread_id}_sub_{task_id or 'x'}",
            metadata=state.get("metadata", {}),
        )
    )
    page_content = str(browser_result.get("page_content", "") or "")

    analysis_result = await _maybe_await(
        default_analyst_runner(
            page_content=page_content,
            task_description=task_goal,
            task_type=state.get("task_type", "auto"),
            metadata=state.get("metadata", {}),
        )
    )

    worker_output = {
        "sub_task_id": task_id,
        "priority": priority,
        "target_url": target_url,
        "task_goal": task_goal,
        "page_content": page_content,
        "analysis_summary": analysis_result.get("summary", ""),
        "analysis_structured": analysis_result.get("structured_json", {}),
    }
    return {
        "worker_outputs": [worker_output],
        "extracted_data": [worker_output.get("analysis_structured", {})],
    }


async def final_summarizer_node(state: AgentState) -> dict[str, Any]:
    outputs = list(state.get("worker_outputs", []))
    if not outputs:
        return {
            "analysis_report": "No worker outputs were produced.",
            "next_step": "end",
        }

    ordered = sorted(outputs, key=lambda x: int(x.get("priority", 1)), reverse=True)
    lines = ["# Daily Intelligence Report", ""]
    plan_summary = state.get("plan_summary", "")
    if plan_summary:
        lines.append(f"Plan Summary: {plan_summary}")
        lines.append("")

    for item in ordered:
        lines.append(f"## SubTask {item.get('sub_task_id', '-')}")
        lines.append(f"- Priority: {item.get('priority', '-')}")
        lines.append(f"- URL: {item.get('target_url', '')}")
        lines.append(f"- Goal: {item.get('task_goal', '')}")
        lines.append(f"- Summary: {item.get('analysis_summary', '')}")
        lines.append("")

    return {
        "analysis_report": "\n".join(lines),
        "next_step": "end",
    }
