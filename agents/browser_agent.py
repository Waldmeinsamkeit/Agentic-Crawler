"""Compatibility module. Prefer importing BrowserExecutor from agents.browser_executor."""

from agents.browser_executor import BrowserExecutor

BrowserAgent = BrowserExecutor

__all__ = ["BrowserExecutor", "BrowserAgent"]
