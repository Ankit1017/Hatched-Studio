from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from groq import Groq


@dataclass(frozen=True)
class CompletionUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class CompletionResult:
    text: str
    usage: CompletionUsage | None = None


class ChatCompletionClient(Protocol):
    def complete(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        messages: list[dict[str, str]],
    ) -> str:
        ...


@runtime_checkable
class ChatCompletionMetadataClient(Protocol):
    def complete_with_metadata(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        messages: list[dict[str, str]],
    ) -> CompletionResult:
        ...


class GroqChatCompletionClient:
    def complete(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        messages: list[dict[str, str]],
    ) -> str:
        return self.complete_with_metadata(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
        ).text

    def complete_with_metadata(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        messages: list[dict[str, str]],
    ) -> CompletionResult:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            temperature=float(temperature),
            max_tokens=int(max_tokens),
            messages=messages,
        )
        text = completion.choices[0].message.content if completion.choices else "No response received."
        usage = self._extract_usage(completion)
        return CompletionResult(text=text, usage=usage)

    @staticmethod
    def _extract_usage(completion: object) -> CompletionUsage | None:
        usage = getattr(completion, "usage", None)
        if usage is None:
            return None
        try:
            prompt_tokens = max(int(getattr(usage, "prompt_tokens", 0) or 0), 0)
            completion_tokens = max(int(getattr(usage, "completion_tokens", 0) or 0), 0)
            total_tokens = max(int(getattr(usage, "total_tokens", 0) or 0), prompt_tokens + completion_tokens)
        except (TypeError, ValueError):
            return None
        return CompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
