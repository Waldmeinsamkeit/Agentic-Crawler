"""Compatibility module. Prefer importing analysts from agents.intelligence package."""

from agents.intelligence import (
    CompetitorAnalyst,
    FinancialAnalyst,
    GeneralAnalyst,
    create_intelligence_agent,
)

__all__ = [
    "GeneralAnalyst",
    "CompetitorAnalyst",
    "FinancialAnalyst",
    "create_intelligence_agent",
]
