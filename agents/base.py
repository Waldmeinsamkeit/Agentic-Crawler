from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel


class BaseAgent(ABC):
    """Common contract for all executable specialists."""

    def __init__(
        self,
        model: BaseChatModel,
        fallback_model: BaseChatModel | None = None,
    ) -> None:
        self.model = model
        self.fallback_model = fallback_model

    @abstractmethod
    async def run(self, input_data: Any, **kwargs: Any) -> Any:
        """Execute the specialist task and return structured output."""

