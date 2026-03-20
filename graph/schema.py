from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScrapeTaskInput(BaseModel):
    task_description: str = Field(..., description="Natural language crawling goal.")
    task_type: str = Field(default="general", description="Task domain, e.g. general/ecommerce/finance.")
    urls: list[str] = Field(default_factory=list, description="Seed URLs to visit.")
    max_steps: int = Field(default=3, ge=1, le=20, description="Max browser-analysis loops.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional runtime context.")
    thread_id: str | None = Field(
        default=None,
        description="Stable run id for checkpoint resume. Use same id to continue.",
    )


class BrowserResult(BaseModel):
    current_url: str = Field(default="", description="Current page URL after execution.")
    page_content: str = Field(default="", description="Main extracted page content.")
    screenshot_path: str | None = Field(default=None, description="Optional screenshot path.")
    raw: dict[str, Any] = Field(default_factory=dict, description="Raw result payload.")


class AnalysisResult(BaseModel):
    structured_json: dict[str, Any] = Field(default_factory=dict, description="Structured extracted data.")
    summary: str = Field(default="", description="Human-readable summary for this analysis step.")
    need_more_data: bool = Field(default=False, description="Whether to continue browsing.")
    raw: dict[str, Any] = Field(default_factory=dict, description="Raw analysis payload.")


class ScrapeTaskOutput(BaseModel):
    analysis_report: str = Field(default="")
    extracted_data: list[dict[str, Any]] = Field(default_factory=list)
    visited_url: str = Field(default="")
    step_count: int = Field(default=0)
    error_count: int = Field(default=0)
    last_successful_url: str = Field(default="")
    status: str = Field(default="completed")
