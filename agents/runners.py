from __future__ import annotations

from typing import Any

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
    analyst = create_intelligence_agent(task_type=task_type, model=model, fallback_model=fallback)
    return await analyst.run(page_content, task_description=task_description, **kwargs)
