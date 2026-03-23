from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from agents.base import BaseAgent
from config import settings


class BrowserExecutor(BaseAgent):
    """
    Specialist for browser-use execution.

    The graph node only needs to pass task input. Browser setup stays here.
    """

    _browser_lock: asyncio.Lock | None = None
    _shared_cdp_url: str | None = None
    _semaphore: asyncio.Semaphore | None = None

    async def run(self, input_data: str | dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        task = input_data if isinstance(input_data, str) else input_data.get("task_description", "")
        urls = kwargs.get("urls") or (input_data.get("urls") if isinstance(input_data, dict) else []) or []
        thread_id = kwargs.get("thread_id") or (
            input_data.get("thread_id", "") if isinstance(input_data, dict) else ""
        )
        thread_id = str(thread_id or "default_user")
        resume_from_url = kwargs.get("resume_from_url") or (
            input_data.get("resume_from_url", "") if isinstance(input_data, dict) else ""
        )
        visited_urls = kwargs.get("visited_urls") or (
            input_data.get("visited_urls", []) if isinstance(input_data, dict) else []
        )

        task_parts = [task]
        if resume_from_url:
            task_parts.append(
                f"Resume from this URL first: {resume_from_url}. Do not repeat earlier navigation."
            )
        if urls:
            task_parts.append(f"Seed URLs: {', '.join(urls)}")
        if visited_urls:
            task_parts.append(
                f"Already visited URLs: {', '.join(visited_urls)}. Prefer unexplored pages."
            )
        task_with_urls = "\n".join([part for part in task_parts if part]).strip()

        semaphore = self._get_semaphore()
        async with semaphore:
            try:
                history = await self._run_once(task_with_urls, llm=self.model, thread_id=thread_id)
            except Exception:
                if not self.fallback_model:
                    raise
                history = await self._run_once(task_with_urls, llm=self.fallback_model, thread_id=thread_id)

        payload = self._history_to_payload(history)
        return {
            "current_url": payload.get("current_url", ""),
            "page_content": payload.get("page_content", ""),
            "screenshot_path": payload.get("screenshot_path"),
            "raw": payload,
        }

    async def _run_once(self, task: str, llm: Any, thread_id: str) -> Any:
        # Ensure browser-use official cloud/api settings are applied at runtime.
        os.environ.setdefault("BROWSER_USE_LLM_URL", settings.BROWSER_USE_LLM_URL)
        os.environ.setdefault("BROWSER_USE_CLOUD_API_URL", settings.BROWSER_USE_CLOUD_API_URL)
        os.environ.setdefault(
            "BROWSER_USE_CLOUD_SYNC",
            "true" if settings.BROWSER_USE_CLOUD_SYNC else "false",
        )
        if settings.BROWSER_USE_API_KEY:
            os.environ.setdefault("BROWSER_USE_API_KEY", settings.BROWSER_USE_API_KEY)

        from browser_use import Agent as BrowserUseAgent
        from browser_use import Browser
        from browser_use import BrowserProfile
        from browser_use import BrowserSession

        contexts_dir = settings.checkpoints_dir / "contexts"
        contexts_dir.mkdir(parents=True, exist_ok=True)
        context_path = contexts_dir / thread_id
        context_path.mkdir(parents=True, exist_ok=True)

        profile = BrowserProfile(
            user_data_dir=context_path.as_posix(),
            headless=settings.HEADLESS,
            disable_security=True,
            wait_for_network_idle_page_load_time=3.0,
        )

        browser_session = None
        if settings.BROWSER_USE_USE_CLOUD_BROWSER:
            browser_session = BrowserSession(
                browser_profile=profile,
                use_cloud=True,
                cloud_profile_id=settings.BROWSER_USE_CLOUD_PROFILE_ID,
                cloud_proxy_country_code=settings.BROWSER_USE_CLOUD_PROXY_COUNTRY_CODE,
                cloud_timeout=settings.BROWSER_USE_CLOUD_TIMEOUT,
            )
        else:
            cdp_url = await self._ensure_shared_browser_and_get_cdp_url(Browser)
            if cdp_url:
                browser_session = BrowserSession(cdp_url=cdp_url, browser_profile=profile)
            else:
                browser_session = BrowserSession(browser_profile=profile)

        agent = BrowserUseAgent(
            task=task,
            llm=llm,
            browser_session=browser_session,
            use_judge=settings.BROWSER_USE_USE_JUDGE,
        )
        return await agent.run()

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(max(1, int(settings.MAX_CONCURRENT_TASKS)))
        return cls._semaphore

    @classmethod
    async def _ensure_shared_browser_and_get_cdp_url(cls, browser_cls: Any) -> str | None:
        if cls._browser_lock is None:
            cls._browser_lock = asyncio.Lock()

        async with cls._browser_lock:
            if cls._shared_cdp_url:
                return cls._shared_cdp_url

            try:
                shared_browser = browser_cls(
                    headless=settings.HEADLESS,
                    disable_security=True,
                    keep_alive=True,
                    wait_for_network_idle_page_load_time=3.0,
                )
                await shared_browser.start()
                cls._shared_cdp_url = getattr(shared_browser, "cdp_url", None)
            except Exception:
                cls._shared_cdp_url = None

            return cls._shared_cdp_url

    @staticmethod
    def _history_to_payload(history: Any) -> dict[str, Any]:
        content = ""
        current_url = ""
        screenshots: list[str] = []
        raw: dict[str, Any] = {}

        if hasattr(history, "last_result"):
            try:
                content = history.last_result() or ""
            except Exception:  # noqa: BLE001
                content = ""

        if not content and hasattr(history, "final_result"):
            try:
                content = history.final_result() or ""
            except Exception:  # noqa: BLE001
                content = ""

        if hasattr(history, "model_dump"):
            try:
                raw = history.model_dump() or {}
            except Exception:  # noqa: BLE001
                raw = {}

        if not content and isinstance(raw, dict):
            for key in ("final_result", "result", "final_answer", "done_text", "text"):
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    content = value.strip()
                    break

            if not content:
                history_items = raw.get("history") or raw.get("all_results") or []
                if isinstance(history_items, list):
                    for item in reversed(history_items):
                        if not isinstance(item, dict):
                            continue
                        for key in ("result", "final_result", "extracted_content", "text"):
                            value = item.get(key)
                            if isinstance(value, str) and value.strip():
                                content = value.strip()
                                break
                        if content:
                            break

        current_url = str(raw.get("url", raw.get("current_url", "")) or "")
        screenshots = raw.get("screenshots") or []
        screenshot_path = screenshots[-1] if screenshots else None

        return {
            "current_url": current_url,
            "page_content": content,
            "screenshot_path": screenshot_path,
            "screenshots": screenshots,
            "history": raw,
        }
