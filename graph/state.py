from __future__ import annotations

from dataclasses import dataclass
from operator import add
from typing import Any, Awaitable, Callable, Literal

from typing_extensions import Annotated, NotRequired, TypedDict


class BrowserRunner(Callable[..., Awaitable[Any]]):
    """Type alias marker for injected browser execution callable."""


class AnalystRunner(Callable[..., Awaitable[Any]]):
    """Type alias marker for injected intelligence analysis callable."""


@dataclass(slots=True)
class GraphServices:
    """
    Runtime service container.

    Keep execution details outside graph logic so nodes remain easy to test.
    """

    browser_runner: Callable[..., Any]
    analyst_runner: Callable[..., Any]


class AgentState(TypedDict):
    # Task input
    task_description: str
    task_type: str
    urls: list[str]
    max_steps: int
    step_count: int

    # Browser execution state
    current_url: str
    last_successful_url: str
    current_page_content: str
    screenshot_history: Annotated[list[str], add]
    visited_urls: Annotated[list[str], add]

    # Intelligence analysis state
    extracted_data: Annotated[list[dict[str, Any]], add]
    analysis_report: str

    # Routing and reliability
    next_step: Literal["continue", "end", "retry"]
    error_count: int
    last_error: str
    requires_human_input: NotRequired[bool]
    human_note: NotRequired[str]

    # Runtime-only dependencies (not meant for persistence)
    services: NotRequired[GraphServices]
    metadata: NotRequired[dict[str, Any]]
