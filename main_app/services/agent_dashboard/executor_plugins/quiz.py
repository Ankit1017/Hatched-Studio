from __future__ import annotations

from main_app.contracts import IntentPayload
from main_app.models import AgentAssetResult, GroqSettings
from main_app.services.agent_dashboard.executor_types import (
    AssetExecutor,
    AssetExecutorPlugin,
    AssetExecutorPluginContext,
)
from main_app.services.agent_dashboard.executor_plugins.parsed_asset_result import (
    build_parsed_asset_result,
)


def _build_executor(context: AssetExecutorPluginContext) -> AssetExecutor:
    def _execute(payload: IntentPayload, settings: GroqSettings) -> AgentAssetResult:
        topic = str(payload.get("topic", ""))
        result = context.quiz_service.generate_quiz(
            topic=topic,
            question_count=int(payload.get("question_count", 10)),
            difficulty=str(payload.get("difficulty", "Intermediate")),
            constraints=str(payload.get("constraints", "")),
            settings=settings,
        )
        return build_parsed_asset_result(
            intent="quiz",
            payload=payload,
            topic=topic,
            title_prefix="Quiz",
            parsed_content=result.parsed_quiz,
            parse_error=result.parse_error,
            raw_text=result.raw_text,
            parse_note=result.parse_note,
            cache_hit=False,
            failure_message="Quiz generation failed.",
        )

    return _execute


PLUGIN = AssetExecutorPlugin(intent="quiz", build_executor=_build_executor)
