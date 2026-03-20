from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agents.intelligence.general import GeneralAnalyst


class CompetitorSchema(BaseModel):
    brand: str = Field(default="")
    product_name: str = Field(default="")
    price: str = Field(default="")
    key_features: list[str] = Field(default_factory=list)
    user_feedback: list[str] = Field(default_factory=list)
    summary: str = Field(default="")
    need_more_data: bool = Field(default=False)


class CompetitorAnalyst(GeneralAnalyst):
    async def run(self, input_data: str, **kwargs: Any) -> dict[str, Any]:
        task_description = kwargs.get("task_description", "")
        prompt = (
            "你是竞品监控分析专家。"
            "请从内容中提取品牌、产品、价格、核心功能、用户评价，最后给出总结。\n"
            f"任务描述: {task_description}\n"
            f"网页内容:\n{input_data}"
        )
        try:
            structured = self.model.with_structured_output(CompetitorSchema)
            result = await structured.ainvoke(prompt)
            parsed = result if isinstance(result, CompetitorSchema) else CompetitorSchema.model_validate(result)
            payload = parsed.model_dump()
            return {
                "structured_json": payload,
                "summary": parsed.summary,
                "need_more_data": parsed.need_more_data,
                "raw": payload,
            }
        except Exception:
            return await self._invoke_with_optional_structure(prompt)

