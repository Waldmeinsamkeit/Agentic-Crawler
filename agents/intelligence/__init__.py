from .competitor import CompetitorAnalyst
from .financial import FinancialAnalyst
from .general import GeneralAnalyst


def create_intelligence_agent(task_type: str, model, fallback_model=None):
    """
    Build a specialist analyst by task type.

    Supported examples:
    - ecommerce / competitor: competitor analyst
    - finance / financial: financial analyst
    - other: general analyst
    """
    normalized = (task_type or "general").strip().lower()
    if normalized in {"ecommerce", "competitor", "competition"}:
        return CompetitorAnalyst(model=model, fallback_model=fallback_model)
    if normalized in {"finance", "financial"}:
        return FinancialAnalyst(model=model, fallback_model=fallback_model)
    return GeneralAnalyst(model=model, fallback_model=fallback_model)


__all__ = [
    "GeneralAnalyst",
    "CompetitorAnalyst",
    "FinancialAnalyst",
    "create_intelligence_agent",
]

