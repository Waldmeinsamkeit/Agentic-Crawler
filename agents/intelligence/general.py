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
    async def run(self, browser_content: str, **kwargs: Any) -> dict[str, Any]:
        prompt = (
            "你是“通用情报分析员（General Analyst）”。\n"
            "请严格基于输入文本进行分析，禁止编造、禁止引入外部知识。\n\n"
            "输入：\n"
            f"{browser_content}\n\n"
            "目标：\n"
            "1) 提取关键信息并结构化；\n"
            "2) 给出简洁结论；\n"
            "3) 标注不确定项与证据来源。\n\n"
            "规则：\n"
            "- 只输出输入中能找到证据的信息；\n"
            "- 不确定就写 null 或 “insufficient_evidence”；\n"
            "- 相同信息去重；\n"
            "- 保留时间、主体、事件、数值、来源线索（若有）；\n"
            "- 每条关键信息都附 evidence_quote（原文片段）。\n\n"
            "输出格式（严格 JSON）：\n"
            "{\n"
            '  "summary": "不超过150字的总体结论",\n'
            '  "key_points": [\n'
            "    {\n"
            '      "topic": "主题",\n'
            '      "entity": "主体/公司/人物",\n'
            '      "event": "发生了什么",\n'
            '      "time": "时间（若未知为null）",\n'
            '      "value": "关键数值（若未知为null）",\n'
            '      "importance": 1,\n'
            '      "evidence_quote": "原文证据片段"\n'
            "    }\n"
            "  ],\n"
            '  "risks_or_uncertainties": [\n'
            "    {\n"
            '      "item": "不确定点",\n'
            '      "reason": "为何不确定"\n'
            "    }\n"
            "  ],\n"
            '  "next_actions": [\n'
            '    "建议下一步抓取或验证动作"\n'
            "  ]\n"
            "}"
        )
        return await self._invoke_with_optional_structure(prompt)

    async def _invoke_with_optional_structure(self, prompt: str) -> dict[str, Any]:
        try:
            structured = self.model.with_structured_output(GeneralAnalysisSchema)
            result = await structured.ainvoke(prompt)
            parsed = (
                result
                if isinstance(result, GeneralAnalysisSchema)
                else GeneralAnalysisSchema.model_validate(result)
            )
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
