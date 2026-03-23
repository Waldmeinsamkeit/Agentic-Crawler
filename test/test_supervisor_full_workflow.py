from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.supervisor import SubTask, TaskPlan
from graph.workflow import create_full_graph
from utils.model_factory import ModelFactory


class TestSupervisorFullWorkflow(unittest.IsolatedAsyncioTestCase):
    async def test_supervisor_decompose_dispatch_and_reduce(self) -> None:
        async def fake_create_plan(self, daily_command: str):  # noqa: ARG001
            return TaskPlan(
                plan_summary="Collect AI funding updates from multiple sources.",
                tasks=[
                    SubTask(
                        id=1,
                        target_url="https://site-a.example/news",
                        task_goal="Find latest AI funding article and key numbers",
                        priority=5,
                    ),
                    SubTask(
                        id=2,
                        target_url="https://site-b.example/ai",
                        task_goal="Extract major AI investment announcements",
                        priority=3,
                    ),
                ],
            )

        async def fake_browser_runner(**kwargs):
            url = (kwargs.get("urls") or [""])[0]
            return {
                "current_url": url,
                "page_content": f"Captured content from {url}",
                "screenshot_path": None,
                "raw": {},
            }

        async def fake_analyst_runner(**kwargs):
            page_content = kwargs.get("page_content", "")
            return {
                "structured_json": {
                    "topic": "ai_funding",
                    "evidence": page_content,
                },
                "summary": f"Summary from {page_content}",
                "need_more_data": False,
                "raw": {},
            }

        initial_state = {
            "task_description": "Daily command: collect AI funding intelligence",
            "task_type": "auto",
            "metadata": {
                "task_id": "test_daily_001",
                "thread_id": "thread_daily_001",
            },
            "worker_outputs": [],
            "extracted_data": [],
        }

        with patch.object(ModelFactory, "get_model", return_value=object()), patch.object(
            ModelFactory, "get_fallback_model", return_value=object()
        ), patch(
            "graph.nodes.supervisor.SupervisorAgent.create_plan",
            new=fake_create_plan,
        ), patch(
            "graph.nodes.supervisor.default_browser_runner",
            new=fake_browser_runner,
        ), patch(
            "graph.nodes.supervisor.default_analyst_runner",
            new=fake_analyst_runner,
        ):
            app = create_full_graph()
            final_state = await app.ainvoke(initial_state)

        self.assertEqual(final_state.get("next_step"), "end")
        self.assertIn("Daily Intelligence Report", final_state.get("analysis_report", ""))
        self.assertIn("SubTask 1", final_state.get("analysis_report", ""))
        self.assertIn("SubTask 2", final_state.get("analysis_report", ""))

        worker_outputs = final_state.get("worker_outputs", [])
        self.assertEqual(len(worker_outputs), 2)
        urls = {item.get("target_url") for item in worker_outputs}
        self.assertSetEqual(
            urls,
            {"https://site-a.example/news", "https://site-b.example/ai"},
        )

        extracted_data = final_state.get("extracted_data", [])
        self.assertEqual(len(extracted_data), 2)
        self.assertTrue(all("topic" in item for item in extracted_data))


if __name__ == "__main__":
    unittest.main()
