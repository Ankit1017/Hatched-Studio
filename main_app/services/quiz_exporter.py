from __future__ import annotations

from typing import Any, Protocol


class QuizExporter(Protocol):
    def list_templates(self) -> list[dict[str, str]]: ...

    def build_question_paper_pdf(
        self,
        *,
        topic: str,
        questions: list[dict[str, Any]],
        template_key: str,
    ) -> tuple[bytes | None, str | None]: ...
