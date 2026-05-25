"""Central guardrails gateway for OpenAI-compatible LLM calls."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Any


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\-\s().]{7,}\d)(?!\d)")


class LLMGatewayError(Exception):
    """Raised when the gateway cannot complete a controlled LLM call."""


@dataclass(slots=True)
class LLMGatewayMetadata:
    """Observable metadata for one LLM gateway call."""

    purpose: str
    model: str
    response_format_type: str
    fallback_used: bool
    latency_ms: float
    redaction_counts: dict[str, int]
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LLMGatewayResponse:
    """Structured response from the LLM gateway."""

    content: str
    payload: dict[str, Any] | None
    metadata: LLMGatewayMetadata


@dataclass(slots=True)
class LLMGateway:
    """Guarded interface for JSON-producing OpenAI-compatible chat calls."""

    client: Any | None = None
    model: str | None = None
    temperature: float = 0
    base_url: str | None = None
    redaction_enabled: bool = True
    metadata_history: list[LLMGatewayMetadata] = field(default_factory=list)

    def call_json(
        self,
        *,
        system_prompt: str,
        user_content: str,
        response_format: dict[str, Any],
        purpose: str,
    ) -> LLMGatewayResponse:
        """Call the model and parse a JSON object response."""

        client = self.client or self._build_default_client()
        model = self.model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        guarded_user_content, redaction_counts = self._redact_user_content(user_content)
        request_payload = {
            "model": model,
            "temperature": self.temperature,
            "response_format": response_format,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": guarded_user_content},
            ],
        }

        started = perf_counter()
        fallback_used = False
        try:
            completion = client.chat.completions.create(**request_payload)
        except Exception as exc:
            if response_format == {"type": "json_object"}:
                metadata = self._metadata(
                    purpose=purpose,
                    model=model,
                    response_format_type="json_object",
                    fallback_used=False,
                    started=started,
                    redaction_counts=redaction_counts,
                    error=str(exc),
                )
                self.metadata_history.append(metadata)
                raise LLMGatewayError(f"LLM gateway call failed: {exc}") from exc

            request_payload["response_format"] = {"type": "json_object"}
            fallback_used = True
            completion = client.chat.completions.create(**request_payload)

        content = completion.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            metadata = self._metadata(
                purpose=purpose,
                model=model,
                response_format_type=self._response_format_type(request_payload["response_format"]),
                fallback_used=fallback_used,
                started=started,
                redaction_counts=redaction_counts,
                completion=completion,
                error="empty_json_content",
            )
            self.metadata_history.append(metadata)
            raise LLMGatewayError("LLM gateway returned empty JSON content.")

        payload: dict[str, Any] | None
        try:
            parsed = json.loads(content)
            payload = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            payload = None

        metadata = self._metadata(
            purpose=purpose,
            model=model,
            response_format_type=self._response_format_type(request_payload["response_format"]),
            fallback_used=fallback_used,
            started=started,
            redaction_counts=redaction_counts,
            completion=completion,
            error=None if payload is not None else "invalid_json_response",
        )
        self.metadata_history.append(metadata)
        return LLMGatewayResponse(content=content, payload=payload, metadata=metadata)

    def _build_default_client(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMGatewayError(
                "LLM gateway requested but OPENAI_API_KEY was not configured."
            )

        try:
            from openai import OpenAI

            return OpenAI(
                api_key=api_key,
                base_url=self.base_url or os.getenv("OPENAI_BASE_URL") or None,
            )
        except ModuleNotFoundError as exc:
            raise LLMGatewayError(
                "The openai package is not installed in the current environment."
            ) from exc

    def _redact_user_content(self, content: str) -> tuple[str, dict[str, int]]:
        if not self.redaction_enabled:
            return content, {"emails": 0, "phones": 0}

        redacted, email_count = EMAIL_RE.subn("[REDACTED_EMAIL]", content)
        redacted, phone_count = PHONE_RE.subn("[REDACTED_PHONE]", redacted)
        return redacted, {"emails": email_count, "phones": phone_count}

    def _metadata(
        self,
        *,
        purpose: str,
        model: str,
        response_format_type: str,
        fallback_used: bool,
        started: float,
        redaction_counts: dict[str, int],
        completion: Any | None = None,
        error: str | None = None,
    ) -> LLMGatewayMetadata:
        usage = getattr(completion, "usage", None)
        return LLMGatewayMetadata(
            purpose=purpose,
            model=model,
            response_format_type=response_format_type,
            fallback_used=fallback_used,
            latency_ms=round((perf_counter() - started) * 1000, 2),
            redaction_counts=dict(redaction_counts),
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            error=error,
        )

    def _response_format_type(self, response_format: dict[str, Any]) -> str:
        raw_type = response_format.get("type")
        return str(raw_type) if raw_type else "unknown"
