from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from agents.base import BaseAgent


class GeneralAnalysisSchema(BaseModel):
    summary: str = Field(default="")
    structured_json: dict[str, Any] = Field(default_factory=dict)
    need_more_data: bool = Field(default=False)


class GeneralAnalyst(BaseAgent):
    async def run(self, input_data: str, **kwargs: Any) -> dict[str, Any]:
        task_description = kwargs.get("task_description", "")
        prompt = (
            "你是通用情报分析专家。"
            "请基于网页内容提炼核心信息，输出摘要与结构化结果。\n"
            f"任务描述: {task_description}\n"
            f"网页内容:\n{input_data}"
        )
        return await self._invoke_with_optional_structure(prompt)

    async def _invoke_with_optional_structure(self, prompt: str) -> dict[str, Any]:
        try:
            structured = self.model.with_structured_output(GeneralAnalysisSchema)
            result = await structured.ainvoke(prompt)
            parsed = result if isinstance(result, GeneralAnalysisSchema) else GeneralAnalysisSchema.model_validate(result)
            return {
                "structured_json": parsed.structured_json,
                "summary": parsed.summary,
                "need_more_data": parsed.need_more_data,
                "raw": parsed.model_dump(),
            }
        except Exception:
            model = self.fallback_model or self.model
            text = await self._invoke_text(model, prompt)
            return {
                "structured_json": {"raw_text": text},
                "summary": text[:500],
                "need_more_data": False,
                "raw": {"text": text},
            }

    @staticmethod
    async def _invoke_text(model: Any, prompt: str) -> str:
        response = await model.ainvoke(prompt)
        if isinstance(response, AIMessage):
            return str(response.content)
        return str(getattr(response, "content", response))

