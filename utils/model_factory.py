from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel

Scene = Literal["browser", "analysis", "general"]


@dataclass(frozen=True, slots=True)
class ModelSpec:
    provider: str
    model_name: str
    vision: bool


class ModelFactory:
    """Unified chat-model factory for LangGraph nodes and browser-use."""

    SCENE_BROWSER: Scene = "browser"
    SCENE_ANALYSIS: Scene = "analysis"
    SCENE_GENERAL: Scene = "general"

    _SCENE_DEFAULTS: dict[Scene, dict[str, Any]] = {
        SCENE_BROWSER: {
            "provider": "openai",
            "model_name": "gpt-4o",
            "temperature": 0.0,
            "require_vision": True,
        },
        SCENE_ANALYSIS: {
            "provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.2,
            "require_vision": False,
        },
        SCENE_GENERAL: {
            "provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.0,
            "require_vision": False,
        },
    }

    # Heuristic list, used to protect browser-use from non-vision models.
    _VISION_MODEL_HINTS: tuple[str, ...] = (
        "gpt-4o",
        "o4",
        "claude-3-5-sonnet",
        "claude-3-7-sonnet",
        "claude-sonnet-4",
        "gemini-1.5-pro",
        "gemini-2.0",
        "gemini-2.5",
        "deepseek-vl",
        "qvq",
        "qwen-image",
        "qwen2.5-vl",
        "llava",
        "qwen-vl",
    )

    _FALLBACK_BY_SCENE: dict[Scene, list[ModelSpec]] = {
        SCENE_BROWSER: [
            ModelSpec("openai", "gpt-4o", True),
            ModelSpec("browser-use", "bu-latest", True),
            ModelSpec("anthropic", "claude-3-5-sonnet-20240620", True),
            ModelSpec("google", "gemini-1.5-pro", True),
        ],
        SCENE_ANALYSIS: [
            ModelSpec("openai", "gpt-4o-mini", False),
            ModelSpec("deepseek", "deepseek-chat", False),
            ModelSpec("qwen", "qwen-plus", False),
            ModelSpec("anthropic", "claude-3-5-haiku-20241022", False),
            ModelSpec("google", "gemini-1.5-flash", False),
            ModelSpec("ollama", "llama3.1", False),
        ],
        SCENE_GENERAL: [
            ModelSpec("openai", "gpt-4o-mini", False),
            ModelSpec("deepseek", "deepseek-chat", False),
            ModelSpec("qwen", "qwen-plus", False),
            ModelSpec("anthropic", "claude-3-5-sonnet-20240620", True),
            ModelSpec("ollama", "llama3.1", False),
        ],
    }

    @classmethod
    def get_model(
        cls,
        provider: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        scene: Scene = SCENE_GENERAL,
        require_vision: bool | None = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """
        Return a LangChain BaseChatModel while masking provider parameter differences.
        """
        scene_defaults = cls._resolve_scene_defaults(scene)

        resolved_provider = (provider or scene_defaults["provider"]).lower()
        resolved_model = model_name or scene_defaults["model_name"]
        resolved_temperature = (
            scene_defaults["temperature"] if temperature is None else temperature
        )
        resolved_require_vision = (
            scene_defaults["require_vision"]
            if require_vision is None
            else require_vision
        )

        if resolved_require_vision:
            cls.validate_vision_capability(resolved_provider, resolved_model)

        cfg = None
        try:
            from config import settings as cfg
        except Exception:  # noqa: BLE001
            cfg = None

        if resolved_provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=resolved_model,
                temperature=resolved_temperature,
                api_key=os.getenv("OPENAI_API_KEY") or (cfg.OPENAI_API_KEY if cfg else None),
                **kwargs,
            )

        if resolved_provider in {"browser-use", "browser_use", "browseruse"}:
            from browser_use.llm.browser_use.chat import ChatBrowserUse

            return ChatBrowserUse(
                model=resolved_model or "bu-latest",
                api_key=os.getenv("BROWSER_USE_API_KEY") or (cfg.BROWSER_USE_API_KEY if cfg else None),
                base_url=os.getenv("BROWSER_USE_LLM_URL", (cfg.BROWSER_USE_LLM_URL if cfg else "https://llm.api.browser-use.com")),
                **kwargs,
            )

        if resolved_provider == "deepseek":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=resolved_model or "deepseek-chat",
                temperature=resolved_temperature,
                api_key=os.getenv("DEEPSEEK_API_KEY") or (cfg.DEEPSEEK_API_KEY if cfg else None),
                base_url=os.getenv("DEEPSEEK_BASE_URL", (cfg.DEEPSEEK_BASE_URL if cfg else "https://api.deepseek.com/v1")),
                **kwargs,
            )

        if resolved_provider == "qwen":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=resolved_model,
                temperature=resolved_temperature,
                api_key=os.getenv("QWEN_API_KEY") or (cfg.QWEN_API_KEY if cfg else None),
                base_url=os.getenv(
                    "QWEN_BASE_URL",
                    (cfg.QWEN_BASE_URL if cfg else "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                ),
                **kwargs,
            )

        if resolved_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model_name=resolved_model,
                temperature=resolved_temperature,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or (cfg.ANTHROPIC_API_KEY if cfg else None),
                **kwargs,
            )

        if resolved_provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=resolved_model,
                temperature=resolved_temperature,
                google_api_key=os.getenv("GOOGLE_API_KEY") or (cfg.GOOGLE_API_KEY if cfg else None),
                **kwargs,
            )

        if resolved_provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=resolved_model,
                temperature=resolved_temperature,
                base_url=os.getenv("OLLAMA_BASE_URL", (cfg.OLLAMA_BASE_URL if cfg else "http://localhost:11434")),
                **kwargs,
            )

        raise ValueError(
            f"Unsupported provider: {resolved_provider}. "
            "Supported providers: openai, browser-use, deepseek, qwen, anthropic, google, ollama."
        )

    @classmethod
    def get_fallback_specs(cls, scene: Scene = SCENE_BROWSER) -> list[ModelSpec]:
        """Return ordered fallback model specs for the target scene."""
        return list(cls._FALLBACK_BY_SCENE.get(scene, cls._FALLBACK_BY_SCENE[cls.SCENE_GENERAL]))

    @classmethod
    def get_fallback_model(
        cls,
        scene: Scene = SCENE_BROWSER,
        temperature: float | None = None,
        exclude_scene_primary: bool = True,
        **kwargs: Any,
    ) -> BaseChatModel:
        """
        Try fallback chain in order and return the first constructible model.
        """
        scene_defaults = cls._resolve_scene_defaults(scene)
        primary_provider = str(scene_defaults["provider"]).lower()
        primary_model = str(scene_defaults["model_name"]).lower()

        errors: list[str] = []
        for spec in cls.get_fallback_specs(scene):
            if exclude_scene_primary:
                if (
                    spec.provider.lower() == primary_provider
                    and spec.model_name.lower() == primary_model
                ):
                    continue
            try:
                return cls.get_model(
                    provider=spec.provider,
                    model_name=spec.model_name,
                    temperature=temperature,
                    scene=scene,
                    require_vision=spec.vision,
                    **kwargs,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{spec.provider}/{spec.model_name}: {exc}")
                continue

        message = "No fallback model could be initialized.\n" + "\n".join(errors)
        raise RuntimeError(message)

    @classmethod
    def validate_vision_capability(cls, provider: str, model_name: str) -> None:
        """
        Soft heuristic guard: catches obvious non-vision model selections early.
        """
        provider = provider.lower()
        name = model_name.lower()

        if provider in {"browser-use", "browser_use", "browseruse"}:
            return

        if provider == "ollama":
            if not any(hint in name for hint in ("llava", "qwen-vl", "minicpm-v")):
                raise ValueError(
                    "Selected Ollama model is likely non-vision. "
                    "For browser scene, choose a vision model like llava/qwen-vl."
                )
            return

        if any(hint in name for hint in cls._VISION_MODEL_HINTS):
            return

        raise ValueError(
            f"Model '{model_name}' may not support vision. "
            "Set require_vision=False or choose a vision-capable model."
        )

    @classmethod
    def _resolve_scene_defaults(cls, scene: Scene) -> dict[str, Any]:
        if scene not in cls._SCENE_DEFAULTS:
            raise ValueError(
                f"Unsupported scene: {scene}. "
                f"Supported scenes: {', '.join(cls._SCENE_DEFAULTS.keys())}."
            )

        try:
            from config import settings
        except Exception:  # noqa: BLE001
            settings = None

        # Allow env overrides per scene.
        upper = scene.upper()
        default_provider = cls._SCENE_DEFAULTS[scene]["provider"]
        default_model = cls._SCENE_DEFAULTS[scene]["model_name"]
        default_temp = cls._SCENE_DEFAULTS[scene]["temperature"]
        if settings is not None:
            if scene == cls.SCENE_BROWSER:
                default_provider = settings.BROWSER_PROVIDER
                default_model = settings.BROWSER_MODEL_NAME
                default_temp = settings.BROWSER_TEMPERATURE
            elif scene == cls.SCENE_ANALYSIS:
                default_provider = settings.ANALYST_PROVIDER
                default_model = settings.ANALYST_MODEL_NAME
                default_temp = settings.ANALYST_TEMPERATURE
            elif scene == cls.SCENE_GENERAL:
                default_provider = settings.GENERAL_PROVIDER
                default_model = settings.GENERAL_MODEL_NAME
                default_temp = settings.GENERAL_TEMPERATURE

        provider = os.getenv(f"{upper}_LLM_PROVIDER", default_provider)
        model_name = os.getenv(f"{upper}_LLM_MODEL", default_model)
        env_temp = os.getenv(f"{upper}_LLM_TEMPERATURE")
        temperature = (
            float(env_temp)
            if env_temp is not None and env_temp.strip() != ""
            else default_temp
        )

        return {
            "provider": provider,
            "model_name": model_name,
            "temperature": temperature,
            "require_vision": cls._SCENE_DEFAULTS[scene]["require_vision"],
        }
