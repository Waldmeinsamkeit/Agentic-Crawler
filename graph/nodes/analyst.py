from __future__ import annotations

import inspect
from typing import Any

from graph.schema import AnalysisResult
from graph.state import AgentState
from agents.runners import default_analyst_runner
from utils.db_handler import get_db_handler
from utils.model_factory import ModelFactory


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _call_runner_with_compatible_kwargs(runner: Any, **kwargs: Any) -> Any:
    signature = inspect.signature(runner)
    has_var_kwargs = any(
        param.kind == inspect.Parameter.VAR_KEYWORD
        for param in signature.parameters.values()
    )
    if has_var_kwargs:
        return runner(**kwargs)

    accepted = {name: value for name, value in kwargs.items() if name in signature.parameters}
    return runner(**accepted)


async def analyst_node(state: AgentState) -> dict[str, Any]:
    services = state.get("services")
    analyst_runner = services.analyst_runner if services else default_analyst_runner

    llm = ModelFactory.get_model(scene=ModelFactory.SCENE_ANALYSIS)
    try:
        fallback_llm = ModelFactory.get_fallback_model(scene=ModelFactory.SCENE_ANALYSIS)
    except Exception:  # noqa: BLE001
        fallback_llm = None

    try:
        result = await _maybe_await(
            _call_runner_with_compatible_kwargs(
                analyst_runner,
                page_content=state.get("current_page_content", ""),
                task_description=state.get("task_description", ""),
                task_type=state.get("task_type", "general"),
                metadata=state.get("metadata", {}),
                llm=llm,
                fallback_llm=fallback_llm,
            )
        )
        analysis = result if isinstance(result, AnalysisResult) else AnalysisResult.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        return {
            "error_count": state.get("error_count", 0) + 1,
            "last_error": f"analyst_node failed: {exc}",
            "next_step": "retry",
        }

    can_continue = state.get("step_count", 0) < state.get("max_steps", 3)
    next_step = "continue" if analysis.need_more_data and can_continue else "end"

    metadata = state.get("metadata", {})
    task_id = str(metadata.get("task_id", "") or "")
    thread_id = str(metadata.get("thread_id", "") or "")
    if thread_id:
        try:
            db = get_db_handler()
            db.save_intelligence(
                task_id=task_id or thread_id,
                thread_id=thread_id,
                source_url=state.get("current_url", ""),
                category=state.get("task_type", "general"),
                raw_content=state.get("current_page_content", ""),
                structured_data=analysis.structured_json,
                summary=analysis.summary,
            )
        except Exception:  # noqa: BLE001
            # Do not block graph progression on business-db transient failures.
            pass

    return {
        "extracted_data": [analysis.structured_json],
        "analysis_report": analysis.summary,
        "next_step": next_step,
    }
