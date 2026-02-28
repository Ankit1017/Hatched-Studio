from __future__ import annotations

from typing import Protocol


class ReportExporter(Protocol):
    def list_templates(self) -> list[dict[str, str]]: ...

    def build_pdf(
        self,
        *,
        topic: str,
        format_title: str,
        markdown_content: str,
        template_key: str,
    ) -> tuple[bytes | None, str | None]: ...
