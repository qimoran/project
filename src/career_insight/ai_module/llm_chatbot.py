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

        wire_api = self.settings.llm_wire_api.strip().lower().replace("-", "_")
        if wire_api in {"responses", "response"}:
            return self._responses(messages, temperature=temperature)
        if wire_api in {"chat_completions", "chat", "chat_completions_api"}:
            return self._chat_completions(messages, temperature=temperature)
        raise ValueError(
            "Unsupported LLM_WIRE_API. Use 'chat_completions' or 'responses'."
        )

    def _chat_completions(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
    ) -> LLMResponse:
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
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

    def _responses(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
    ) -> LLMResponse:
        url = self.settings.llm_base_url.rstrip("/") + "/responses"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        instructions = "\n\n".join(
            message["content"] for message in messages if message.get("role") == "system"
        )
        input_text = "\n\n".join(
            f"{message.get('role', 'user')}: {message.get('content', '')}"
            for message in messages
            if message.get("role") != "system"
        )
        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "input": input_text,
            "temperature": temperature,
        }
        if instructions:
            payload["instructions"] = instructions

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.settings.llm_timeout_seconds,
        )
        self._raise_for_error_response(response)
        data = self._json_response(response)
        return LLMResponse(
            content=self._extract_responses_text(data),
            model=data.get("model") or self.settings.llm_model,
        )

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

    def _extract_responses_text(self, data: dict[str, Any]) -> str:
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        chunks: list[str] = []
        for item in data.get("output", []) or []:
            for content in item.get("content", []) or []:
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        if chunks:
            return "\n".join(chunks)

        choices = data.get("choices")
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content

        raise ValueError("LLM responses payload did not contain output text")
