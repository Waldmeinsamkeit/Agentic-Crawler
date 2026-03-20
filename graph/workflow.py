from __future__ import annotations

import sqlite3
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Iterable

from langgraph.graph import END, StateGraph

from graph.edges import route_after_analyst, route_after_browser
from graph.nodes import analyst_node, browser_node, init_state_node
from graph.state import AgentState


def create_memory_checkpointer() -> Any:
    """
    Create in-memory checkpointer for local development.
    """
    try:
        from langgraph.checkpoint.memory import MemorySaver
    except ImportError:
        from langgraph.checkpoint.memory import InMemorySaver as MemorySaver
    return MemorySaver()


def create_sqlite_checkpointer(db_path: str = "relics_checkpoints.db") -> Any:
    """
    Create SQLite-backed checkpointer for resumable production runs.
    """
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        warnings.warn(
            "langgraph sqlite checkpointer is not installed. "
            "Falling back to in-memory checkpointer. "
            "Install `langgraph-checkpoint-sqlite` for persistent checkpoints.",
            RuntimeWarning,
            stacklevel=2,
        )
        return create_memory_checkpointer()

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path.as_posix(), check_same_thread=False)
    return SqliteSaver(conn)


@asynccontextmanager
async def create_async_sqlite_checkpointer(
    db_path: str = "relics_checkpoints.db",
) -> AsyncIterator[Any]:
    """
    Create AsyncSqliteSaver for async graph execution (ainvoke/astream).
    """
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except ImportError:
        warnings.warn(
            "Async sqlite checkpointer is not installed. "
            "Falling back to in-memory checkpointer. "
            "Install `langgraph-checkpoint-sqlite` and `aiosqlite` "
            "for persistent async checkpoints.",
            RuntimeWarning,
            stacklevel=2,
        )
        yield create_memory_checkpointer()
        return

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn_string = path.as_posix()
    async with AsyncSqliteSaver.from_conn_string(conn_string) as saver:
        yield saver


def build_run_config(thread_id: str) -> dict[str, Any]:
    """
    Build invoke config for checkpoint recovery.

    Reuse the same thread_id to continue from the latest checkpoint.
    """
    return {"configurable": {"thread_id": thread_id}}


def _normalize_interrupt_nodes(nodes: Iterable[str] | None) -> list[str] | None:
    if not nodes:
        return None

    aliases = {
        "browser_node": "browser",
        "analyst_node": "analyst",
        "init_state_node": "init",
    }
    normalized = [aliases.get(name, name) for name in nodes]
    return normalized


def create_scraping_graph(
    *,
    checkpointer: Any | None = None,
    interrupt_before: Iterable[str] | None = None,
    interrupt_after: Iterable[str] | None = None,
):
    workflow = StateGraph(AgentState)

    workflow.add_node("init", init_state_node)
    workflow.add_node("browser", browser_node)
    workflow.add_node("analyst", analyst_node)

    workflow.set_entry_point("init")
    workflow.add_edge("init", "browser")

    workflow.add_conditional_edges(
        "browser",
        route_after_browser,
        {
            "analyst": "analyst",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "analyst",
        route_after_analyst,
        {
            "browser": "browser",
            "end": END,
        },
    )

    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    normalized_before = _normalize_interrupt_nodes(interrupt_before)
    normalized_after = _normalize_interrupt_nodes(interrupt_after)
    if normalized_before:
        compile_kwargs["interrupt_before"] = normalized_before
    if normalized_after:
        compile_kwargs["interrupt_after"] = normalized_after

    return workflow.compile(**compile_kwargs)
