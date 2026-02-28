from __future__ import annotations

from typing import Any, Protocol


class SlideDeckExporter(Protocol):
    def list_templates(self) -> list[dict[str, str]]: ...

    def build_pptx(
        self,
        *,
        topic: str,
        slides: list[dict[str, Any]],
        template_key: str,
    ) -> tuple[bytes | None, str | None]: ...

    def build_pdf(
        self,
        *,
        topic: str,
        slides: list[dict[str, Any]],
        template_key: str,
    ) -> tuple[bytes | None, str | None]: ...
