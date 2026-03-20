from __future__ import annotations

import inspect
from typing import Any

from graph.schema import BrowserResult
from graph.state import AgentState
from agents.runners import default_browser_runner
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


async def browser_node(state: AgentState) -> dict[str, Any]:
    services = state.get("services")
    browser_runner = services.browser_runner if services else default_browser_runner

    llm = ModelFactory.get_model(scene=ModelFactory.SCENE_BROWSER)
    try:
        fallback_llm = ModelFactory.get_fallback_model(scene=ModelFactory.SCENE_BROWSER)
    except Exception:  # noqa: BLE001
        fallback_llm = None
    resume_from_url = state.get("last_successful_url") or state.get("current_url") or ""
    visited_urls = state.get("visited_urls", [])
    base_task = state.get("task_description", "")
    resume_task = (
        f"Continue from URL: {resume_from_url}. Original task: {base_task}"
        if resume_from_url
        else base_task
    )

    try:
        result = await _maybe_await(
            _call_runner_with_compatible_kwargs(
                browser_runner,
                task_description=resume_task,
                urls=state.get("urls", []),
                resume_from_url=resume_from_url,
                visited_urls=visited_urls,
                step_count=state.get("step_count", 0),
                metadata=state.get("metadata", {}),
                llm=llm,
                fallback_llm=fallback_llm,
            )
        )
        browser_result = result if isinstance(result, BrowserResult) else BrowserResult.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        blocked = any(token in message.lower() for token in ("captcha", "verify", "login", "2fa"))
        return {
            "error_count": state.get("error_count", 0) + 1,
            "last_error": f"browser_node failed: {exc}",
            "requires_human_input": blocked,
            "human_note": "Manual verification required before resume." if blocked else "",
            "next_step": "retry",
        }

    update: dict[str, Any] = {
        "current_url": browser_result.current_url,
        "last_successful_url": browser_result.current_url or resume_from_url,
        "current_page_content": browser_result.page_content,
        "step_count": state.get("step_count", 0) + 1,
        "next_step": "continue",
        "last_error": "",
        "requires_human_input": False,
        "human_note": "",
    }
    if browser_result.current_url:
        update["visited_urls"] = [browser_result.current_url]
    if browser_result.screenshot_path:
        update["screenshot_history"] = [browser_result.screenshot_path]
    return update
