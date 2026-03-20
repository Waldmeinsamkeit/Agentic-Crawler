from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agents.intelligence.general import GeneralAnalyst


class FinancialSchema(BaseModel):
    company: str = Field(default="")
    revenue: str = Field(default="")
    net_profit: str = Field(default="")
    growth_rate: str = Field(default="")
    risks: list[str] = Field(default_factory=list)
    summary: str = Field(default="")
    need_more_data: bool = Field(default=False)


class FinancialAnalyst(GeneralAnalyst):
    async def run(self, browser_content: str, **kwargs: Any) -> dict[str, Any]:
        task_description = kwargs.get("task_description", "")
        prompt = (
            "You are a financial intelligence analyst.\n"
            "Extract key financial metrics, growth signals, and risk points.\n"
            "Use only the provided browser content.\n\n"
            f"Task Description:\n{task_description}\n\n"
            f"Browser Content:\n{browser_content}"
        )
        try:
            structured = self.model.with_structured_output(FinancialSchema)
            result = await structured.ainvoke(prompt)
            parsed = result if isinstance(result, FinancialSchema) else FinancialSchema.model_validate(result)
            payload = parsed.model_dump()
            return {
                "structured_json": payload,
                "summary": parsed.summary,
                "need_more_data": parsed.need_more_data,
                "raw": payload,
            }
        except Exception:
            return await self._invoke_with_optional_structure(prompt)
