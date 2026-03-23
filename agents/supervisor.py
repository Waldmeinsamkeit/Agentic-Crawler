from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from agents.base import BaseAgent


class SubTask(BaseModel):
    id: int
    target_url: str = Field(description="Specific website URL to crawl.")
    task_goal: str = Field(description="What to collect or do on the target URL.")
    priority: int = Field(default=1, ge=1, le=5, description="Priority from 1(low) to 5(high).")


class TaskPlan(BaseModel):
    plan_summary: str = Field(description="Supervisor understanding of the whole daily command.")
    tasks: list[SubTask] = Field(description="Decomposed parallel subtasks.")


class SupervisorAgent(BaseAgent):
    async def create_plan(self, daily_command: str) -> TaskPlan:
        prompt = f"""
你是一个 AI 爬虫集群总管（Supervisor）。
用户每日指令：{daily_command}

你的职责：
1. 理解目标并确定关键公开信息源（科技媒体、公司官网、公告页）。
2. 将大任务拆解为多个互不干扰、可并行执行的子任务。
3. 每个子任务必须明确可执行（包含目标网址与动作目标）。
4. 输出必须严格符合 TaskPlan 结构。
        """

        # Primary path: structured output
        try:
            planner = self.model.with_structured_output(TaskPlan)
            result = await planner.ainvoke(prompt)
            return result if isinstance(result, TaskPlan) else TaskPlan.model_validate(result)
        except Exception:
            pass

        # Fallback path: ask for JSON text and parse manually
        fallback_prompt = (
            f"{prompt}\n\n"
            "请仅输出 JSON，格式必须是：\n"
            '{"plan_summary":"...","tasks":[{"id":1,"target_url":"https://...","task_goal":"...","priority":3}]}\n'
        )
        try:
            response = await self.model.ainvoke(fallback_prompt)
            text = (
                str(response.content)
                if isinstance(response, AIMessage)
                else str(getattr(response, "content", response))
            )
            payload = self._extract_json_payload(text)
            return TaskPlan.model_validate(payload)
        except Exception:
            # Final safety fallback: always return at least one executable task
            return TaskPlan(
                plan_summary="Fallback plan generated due to model structured output incompatibility.",
                tasks=[
                    SubTask(
                        id=1,
                        target_url="https://techcrunch.com/?s=AI",
                        task_goal=f"Search and summarize key signals for: {daily_command}",
                        priority=3,
                    )
                ],
            )

    async def run(self, input_data: Any, **kwargs: Any) -> Any:
        command = str(input_data if input_data is not None else "")
        return await self.create_plan(command)

    @staticmethod
    def _extract_json_payload(text: str) -> dict[str, Any]:
        # Direct parse first
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        # Find a likely JSON object block
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("No JSON object found in supervisor fallback output.")
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            raise ValueError("Supervisor fallback output is not a JSON object.")
        return data
