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
    fallback_reason: str = ""


class CompatibleLLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.3) -> LLMResponse:
        if not self.settings.llm_configured:
            return LLMResponse(
                content="",
                model=self.settings.llm_model or "not-configured",
                used_fallback=True,
                fallback_reason="未配置 LLM_API_KEY、LLM_BASE_URL 或 LLM_MODEL",
            )

        url = self._chat_url()
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
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
        self._raise_for_error_response(response)
        data = self._json_response(response)
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(content=content, model=self.settings.llm_model)

    def _chat_url(self) -> str:
        base_url = self.settings.llm_base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return base_url + "/chat/completions"

    def _json_response(self, response: requests.Response) -> dict[str, Any]:
        content_type = response.headers.get("Content-Type", "")
        try:
            return response.json()
        except ValueError as exc:
            preview = response.text[:180].replace("\n", " ")
            raise ValueError(
                f"LLM API returned non-JSON content "
                f"(status={response.status_code}, content_type={content_type}, preview={preview})"
            ) from exc

    def _raise_for_error_response(self, response: requests.Response) -> None:
        if response.status_code < 400:
            return
        preview = response.text[:500].replace("\n", " ")
        raise ValueError(
            f"LLM API error status={response.status_code}, "
            f"content_type={response.headers.get('Content-Type', '')}, "
            f"body={preview}"
        )
