from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime configuration with env-based overrides."""

    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent
    CHECKPOINTS_DIR: Path = Field(default=Path("checkpoints"))
    CHECKPOINT_DB_PATH: Optional[Path] = None
    REPORTS_DB_PATH: Optional[Path] = None
    BUSINESS_DB_PATH: Optional[Path] = None
    DATA_DIR: Path = Field(default=Path("data"))
    SCREENSHOT_DIR: Optional[Path] = None

    # MCP
    MCP_SERVER_NAME: str = "AI-Crawler-Agent"
    THREAD_PREFIX: str = "mcp_task"
    INTERRUPT_BEFORE_BROWSER: bool = False

    # Runtime controls
    DEFAULT_MAX_PAGES: int = 3
    RETRY_LIMIT: int = 3
    MAX_CONCURRENT_TASKS: int = 3
    DEFAULT_SCRAPE_TIMEOUT: int = 90
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Optional[Path] = None

    # Browser-use behavior
    HEADLESS: bool = True
    SLOW_MO: int = 500
    BROWSER_USE_API_KEY: Optional[str] = None
    BROWSER_USE_LLM_URL: str = "https://llm.api.browser-use.com"
    BROWSER_USE_LLM_MODEL: str = "bu-latest"
    BROWSER_USE_CLOUD_API_URL: str = "https://api.browser-use.com"
    BROWSER_USE_CLOUD_SYNC: bool = True
    BROWSER_USE_CONFIG_DIR: Optional[Path] = None
    BROWSER_USE_USE_CLOUD_BROWSER: bool = False
    BROWSER_USE_USE_JUDGE: bool = False
    BROWSER_USE_CLOUD_PROFILE_ID: Optional[str] = None
    BROWSER_USE_CLOUD_PROXY_COUNTRY_CODE: Optional[str] = None
    BROWSER_USE_CLOUD_TIMEOUT: Optional[int] = None

    # LLM provider credentials
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    QWEN_API_KEY: Optional[str] = None
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Default model presets for graph scenes
    BROWSER_PROVIDER: str = "browser-use"
    BROWSER_MODEL_NAME: str = "bu-latest"
    BROWSER_TEMPERATURE: float = 0.0

    ANALYST_PROVIDER: str = "openai"
    ANALYST_MODEL_NAME: str = "gpt-4o-mini"
    ANALYST_TEMPERATURE: float = 0.2

    GENERAL_PROVIDER: str = "openai"
    GENERAL_MODEL_NAME: str = "gpt-4o-mini"
    GENERAL_TEMPERATURE: float = 0.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_ignore_empty=True,
    )

    @property
    def checkpoint_db_path(self) -> Path:
        return self.CHECKPOINT_DB_PATH or (self.checkpoints_dir / "relics_state.db")

    @property
    def reports_db_path(self) -> Path:
        if self.REPORTS_DB_PATH:
            return self.REPORTS_DB_PATH
        if self.BUSINESS_DB_PATH:
            return self.BUSINESS_DB_PATH
        return self.base_data_dir / "business.db"

    @property
    def base_data_dir(self) -> Path:
        return self.DATA_DIR if self.DATA_DIR.is_absolute() else self.BASE_DIR / self.DATA_DIR

    @property
    def checkpoints_dir(self) -> Path:
        return self.CHECKPOINTS_DIR if self.CHECKPOINTS_DIR.is_absolute() else self.BASE_DIR / self.CHECKPOINTS_DIR

    @property
    def screenshot_dir(self) -> Path:
        if self.SCREENSHOT_DIR:
            if self.SCREENSHOT_DIR.is_absolute():
                return self.SCREENSHOT_DIR
            return self.BASE_DIR / self.SCREENSHOT_DIR
        return self.BASE_DIR / "outputs" / "screenshots"

    @property
    def log_dir(self) -> Path:
        if self.LOG_DIR:
            if self.LOG_DIR.is_absolute():
                return self.LOG_DIR
            return self.BASE_DIR / self.LOG_DIR
        return self.base_data_dir / "logs"


settings = Settings()
settings.checkpoints_dir.mkdir(parents=True, exist_ok=True)
settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
settings.reports_db_path.parent.mkdir(parents=True, exist_ok=True)
settings.base_data_dir.mkdir(parents=True, exist_ok=True)
settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
settings.log_dir.mkdir(parents=True, exist_ok=True)

# Ensure browser-use can write config in project-scoped directory (avoids OS permission issues)
resolved_browser_use_config_dir = (
    settings.BROWSER_USE_CONFIG_DIR
    if settings.BROWSER_USE_CONFIG_DIR
    else settings.BASE_DIR / ".browseruse"
)
if not resolved_browser_use_config_dir.is_absolute():
    resolved_browser_use_config_dir = settings.BASE_DIR / resolved_browser_use_config_dir
resolved_browser_use_config_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BROWSER_USE_CONFIG_DIR", resolved_browser_use_config_dir.as_posix())
os.environ.setdefault("BROWSER_USE_LLM_URL", settings.BROWSER_USE_LLM_URL)
os.environ.setdefault("BROWSER_USE_CLOUD_API_URL", settings.BROWSER_USE_CLOUD_API_URL)
os.environ.setdefault("BROWSER_USE_CLOUD_SYNC", "true" if settings.BROWSER_USE_CLOUD_SYNC else "false")
if settings.BROWSER_USE_API_KEY:
    os.environ.setdefault("BROWSER_USE_API_KEY", settings.BROWSER_USE_API_KEY)


def load_settings() -> Settings:
    """Backward-compatible accessor."""
    return settings
