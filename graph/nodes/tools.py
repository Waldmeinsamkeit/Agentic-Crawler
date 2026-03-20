from __future__ import annotations

from typing import Any

from graph.state import AgentState


async def init_state_node(state: AgentState) -> dict[str, Any]:
    return {
        "task_type": state.get("task_type", "general"),
        "urls": state.get("urls", []),
        "max_steps": state.get("max_steps", 3),
        "step_count": state.get("step_count", 0),
        "error_count": state.get("error_count", 0),
        "last_successful_url": state.get("last_successful_url", ""),
        "current_url": state.get("current_url", ""),
        "current_page_content": state.get("current_page_content", ""),
        "screenshot_history": state.get("screenshot_history", []),
        "visited_urls": state.get("visited_urls", []),
        "extracted_data": state.get("extracted_data", []),
        "analysis_report": state.get("analysis_report", ""),
        "last_error": state.get("last_error", ""),
        "requires_human_input": state.get("requires_human_input", False),
        "human_note": state.get("human_note", ""),
        "next_step": state.get("next_step", "continue"),
    }
