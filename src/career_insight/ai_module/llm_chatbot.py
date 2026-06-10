from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from career_insight.config.settings import Settings, get_settings


@dataclass
class LLMResponse:
    content: str
    model: str
    used_fallback: bool = False


class CompatibleLLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.3) -> LLMResponse:
        if not self.settings.llm_configured:
            return LLMResponse(
                content="",
                model=self.settings.llm_model or "not-configured",
                used_fallback=True,
            )

        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(content=content, model=self.settings.llm_model)
