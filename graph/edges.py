from __future__ import annotations

from typing import Literal

from config import settings
from graph.state import AgentState


def route_after_browser(state: AgentState) -> Literal["analyst", "end"]:
    if state.get("error_count", 0) >= settings.RETRY_LIMIT:
        return "end"
    if state.get("requires_human_input"):
        return "end"
    if state.get("next_step") == "retry":
        return "end"
    if not state.get("current_page_content"):
        return "end"
    return "analyst"


def route_after_analyst(state: AgentState) -> Literal["browser", "end"]:
    if state.get("error_count", 0) >= settings.RETRY_LIMIT:
        return "end"
    if state.get("next_step") == "continue":
        return "browser"
    return "end"
