from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from agents.browser_executor import BrowserExecutor
from agents.intelligence import create_intelligence_agent
from utils.model_factory import ModelFactory


async def default_browser_runner(
    task_description: str,
    urls: list[str] | None = None,
    llm=None,
    fallback_llm=None,
    **kwargs: Any,
) -> dict[str, Any]:
    model = llm or ModelFactory.get_model(scene=ModelFactory.SCENE_BROWSER)
    if fallback_llm is not None:
        fallback = fallback_llm
    elif llm is not None:
        fallback = None
    else:
        try:
            fallback = ModelFactory.get_fallback_model(scene=ModelFactory.SCENE_BROWSER)
        except Exception:  # noqa: BLE001
            fallback = None
    agent = BrowserExecutor(model=model, fallback_model=fallback)
    return await agent.run(
        {
            "task_description": task_description,
            "urls": urls or [],
        },
        **kwargs,
    )


async def default_analyst_runner(
    page_content: str,
    task_description: str = "",
    task_type: str = "general",
    llm=None,
    fallback_llm=None,
    **kwargs: Any,
) -> dict[str, Any]:
    model = llm or ModelFactory.get_model(scene=ModelFactory.SCENE_ANALYSIS)
    if fallback_llm is not None:
        fallback = fallback_llm
    elif llm is not None:
        fallback = None
    else:
        try:
            fallback = ModelFactory.get_fallback_model(scene=ModelFactory.SCENE_ANALYSIS)
        except Exception:  # noqa: BLE001
            fallback = None
    resolved_task_type = await _resolve_task_type(
        task_type=task_type,
        task_description=task_description,
        page_content=page_content,
        model=model,
    )
    analyst = create_intelligence_agent(
        task_type=resolved_task_type,
        model=model,
        fallback_model=fallback,
    )
    return await analyst.run(page_content, task_description=task_description, **kwargs)


def _normalize_task_type(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"ecommerce", "competitor", "competition"}:
        return "competitor"
    if normalized in {"finance", "financial"}:
        return "financial"
    if normalized in {"general"}:
        return "general"
    return normalized


async def _resolve_task_type(
    *,
    task_type: str,
    task_description: str,
    page_content: str,
    model: Any,
) -> str:
    normalized = _normalize_task_type(task_type)
    if normalized in {"competitor", "financial", "general"}:
        return normalized

    # For tech/auto/unknown labels, let LLM route to an analyst expert.
    prompt = (
        "You are a routing classifier for analyst experts.\n"
        "Choose exactly one label from: general, competitor, financial.\n"
        "Return only the label word, no extra text.\n\n"
        f"Task Description:\n{task_description}\n\n"
        f"Browser Content (truncated):\n{(page_content or '')[:2500]}"
    )
    try:
        response = await model.ainvoke(prompt)
        text = (
            str(response.content)
            if isinstance(response, AIMessage)
            else str(getattr(response, "content", response))
        )
        label = text.strip().lower()
        if "financial" in label or "finance" in label:
            return "financial"
        if "competitor" in label or "competition" in label or "ecommerce" in label:
            return "competitor"
    except Exception:  # noqa: BLE001
        pass

    return "general"
