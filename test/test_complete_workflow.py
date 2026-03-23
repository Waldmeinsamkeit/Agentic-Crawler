from __future__ import annotations

import unittest
from unittest.mock import patch

from graph.state import GraphServices
from graph.workflow import create_scraping_graph
from utils.model_factory import ModelFactory


class TestCompleteWorkflow(unittest.IsolatedAsyncioTestCase):
    async def test_end_to_end_graph_calls_analyst_with_browser_content(self) -> None:
        observed: dict[str, str] = {}

        async def fake_browser_runner(**kwargs):
            observed["browser_task_description"] = kwargs.get("task_description", "")
            return {
                "current_url": "https://example.com/ai-news",
                "page_content": "AI startup Alpha raised $20M on 2026-03-20.",
                "screenshot_path": None,
                "raw": {"source": "fake_browser_runner"},
            }

        async def fake_analyst_runner(**kwargs):
            observed["analyst_page_content"] = kwargs.get("page_content", "")
            observed["analyst_task_type"] = kwargs.get("task_type", "")
            return {
                "structured_json": {
                    "entity": "Alpha",
                    "event": "raised",
                    "value": "$20M",
                    "time": "2026-03-20",
                },
                "summary": "Alpha raised $20M on 2026-03-20.",
                "need_more_data": False,
                "raw": {"source": "fake_analyst_runner"},
            }

        services = GraphServices(
            browser_runner=fake_browser_runner,
            analyst_runner=fake_analyst_runner,
        )

        app = create_scraping_graph()
        initial_state = {
            "task_description": "Find important AI funding news",
            "task_type": "general",
            "urls": [],
            "max_steps": 2,
            "step_count": 0,
            "error_count": 0,
            "screenshot_history": [],
            "visited_urls": [],
            "extracted_data": [],
            "analysis_report": "",
            "next_step": "continue",
            "services": services,
            "metadata": {},
        }

        # Patch model construction to avoid any real API key/model dependency in tests.
        with patch.object(ModelFactory, "get_model", return_value=object()), patch.object(
            ModelFactory, "get_fallback_model", return_value=object()
        ):
            final_state = await app.ainvoke(initial_state)

        self.assertEqual(final_state.get("current_url"), "https://example.com/ai-news")
        self.assertEqual(final_state.get("analysis_report"), "Alpha raised $20M on 2026-03-20.")
        self.assertEqual(len(final_state.get("extracted_data", [])), 1)
        self.assertEqual(final_state.get("next_step"), "end")
        self.assertEqual(final_state.get("step_count"), 1)

        self.assertIn("Find important AI funding news", observed.get("browser_task_description", ""))
        self.assertEqual(
            observed.get("analyst_page_content"),
            "AI startup Alpha raised $20M on 2026-03-20.",
        )
        self.assertEqual(observed.get("analyst_task_type"), "general")


if __name__ == "__main__":
    unittest.main()
