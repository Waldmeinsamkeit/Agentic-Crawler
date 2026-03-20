# AI Crawler Framework

An extensible AI crawler framework built with LangGraph + MCP.

## Architecture

```text
my-agent-framework/
+-- mcp_server.py           # MCP entry, exposes crawler tools/resources
+-- config.py               # Centralized settings via pydantic-settings
+-- main.py                 # Standalone local run entry (no MCP required)
+-- graph/
|   +-- state.py            # LangGraph shared state definition
|   +-- nodes/              # Graph nodes (invoke agents)
|   +-- edges.py            # Routing policy (retry/end/continue)
|   +-- workflow.py         # Graph assembly + checkpointer integration
+-- agents/
|   +-- base.py             # Agent abstract contract
|   +-- browser_executor.py # browser-use execution specialist
|   +-- intelligence/       # Analyst specialists (general/financial/competitor)
+-- utils/
|   +-- model_factory.py    # Unified LLM provider abstraction
|   +-- db_handler.py       # Business DB repository (SQLAlchemy)
+-- checkpoints/            # Checkpointer sqlite files
```

## Key Features

- LangGraph orchestration with resumable execution (`thread_id` + checkpointer)
- MCP tool/resource interface for external clients (Claude/Cursor)
- Model factory abstraction across OpenAI / Anthropic / Google / Ollama / DeepSeek / Qwen
- Specialist-agent design (browser executor + domain analysts)
- Separation of persistence concerns:
  - Checkpointer DB: graph execution state
  - Business DB: final intelligence records and task reports

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Prepare environment:

```bash
cp .env.example .env
```

3. Run standalone task:

```bash
python main.py
```

4. Run MCP server:

```bash
python mcp_server.py
```

## Persistence Strategy

- `graph/workflow.py` uses SQLite checkpointer for resume and interruption recovery.
- `utils/db_handler.py` stores:
  - `task_reports`: task-level summary
  - `intelligence_reports`: per-analysis intelligence output

## Notes

- Use the same `thread_id` to resume from previous checkpoints.
- If browser step is blocked by captcha/login, state is marked for human intervention.
- Configure providers/models through `.env` (see `.env.example`).
