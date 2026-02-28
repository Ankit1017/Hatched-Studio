from __future__ import annotations

import json
import os
import sys
import types
import unittest
from dataclasses import dataclass
from typing import Any

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(
                    create=lambda **_kwargs: types.SimpleNamespace(choices=[])
                )
            )

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

from main_app.models import AgentAssetResult, AgentPlan, GroqSettings
from main_app.parsers.audio_overview_parser import AudioOverviewParser
from main_app.parsers.data_table_parser import DataTableParser
from main_app.parsers.flashcards_parser import FlashcardsParser
from main_app.parsers.intent_parser import IntentParser
from main_app.parsers.mind_map_parser import MindMapParser
from main_app.parsers.quiz_parser import QuizParser
from main_app.parsers.slideshow_parser import SlideShowParser
from main_app.services.agent_dashboard import AgentDashboardService
from main_app.services.agent_dashboard.asset_executor_registry import (
    AgentAssetExecutorRegistry,
    build_default_asset_executor_registry,
)
from main_app.services.asset_history_service import AssetHistoryService
from main_app.services.audio_overview_service import AudioOverviewService
from main_app.services.data_table_service import DataTableService
from main_app.services.flashcards_service import FlashcardsService
from main_app.services.intent import IntentRouterService
from main_app.services.mind_map_service import MindMapService
from main_app.services.quiz_service import QuizService
from main_app.services.report_service import ReportService
from main_app.services.slideshow_service import SlideShowService
from main_app.domains.topic.services.topic_explainer_service import TopicExplainerService
from main_app.services.video_asset_service import VideoAssetService


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


class _ScriptedLLMService:
    def __init__(
        self,
        *,
        responses_by_task: dict[str, str | list[str]],
        errors_by_task: dict[str, Exception] | None = None,
    ) -> None:
        self._responses_by_task: dict[str, list[str]] = {}
        for task, response in responses_by_task.items():
            if isinstance(response, list):
                self._responses_by_task[task] = [str(item) for item in response]
            else:
                self._responses_by_task[task] = [str(response)]
        self._errors_by_task = dict(errors_by_task or {})
        self.calls: list[str] = []

    def call(self, **kwargs: object) -> tuple[str, bool]:
        task = str(kwargs.get("task", "")).strip()
        self.calls.append(task)
        if task in self._errors_by_task:
            raise self._errors_by_task[task]

        responses = self._responses_by_task.get(task)
        if not responses:
            raise AssertionError(f"No scripted response configured for task `{task}`.")

        if len(responses) > 1:
            response = responses.pop(0)
        else:
            response = responses[0]
        return response, False


class _InMemoryAssetHistoryStore:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def list_records(self) -> list[dict[str, Any]]:
        return sorted(
            self._records.values(),
            key=lambda item: str(item.get("created_at", "")),
            reverse=True,
        )

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        key = str(record_id).strip()
        if not key:
            return None
        return self._records.get(key)

    def upsert_record(self, record_entry: dict[str, Any]) -> None:
        record_id = str(record_entry.get("id", "")).strip()
        if not record_id:
            return
        self._records[record_id] = dict(record_entry)

    def save_records(self, records: list[dict[str, Any]]) -> None:
        self._records = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            record_id = str(record.get("id", "")).strip()
            if record_id:
                self._records[record_id] = dict(record)


class _InMemoryQuizHistoryStore:
    def __init__(self) -> None:
        self._quizzes: dict[str, dict[str, Any]] = {}

    def list_quizzes(self) -> list[dict[str, Any]]:
        return list(self._quizzes.values())

    def save_quizzes(self, quizzes: list[dict[str, Any]]) -> None:
        self._quizzes = {}
        for quiz in quizzes:
            if not isinstance(quiz, dict):
                continue
            quiz_id = str(quiz.get("id", "")).strip()
            if quiz_id:
                self._quizzes[quiz_id] = dict(quiz)

    def get_quiz(self, quiz_id: str) -> dict[str, Any] | None:
        return self._quizzes.get(str(quiz_id).strip())

    def upsert_quiz(self, quiz_entry: dict[str, Any]) -> None:
        quiz_id = str(quiz_entry.get("id", "")).strip()
        if not quiz_id:
            return
        self._quizzes[quiz_id] = dict(quiz_entry)


@dataclass
class _FlowHarness:
    registry: AgentAssetExecutorRegistry
    dashboard: AgentDashboardService
    asset_history_service: AssetHistoryService
    quiz_history_store: _InMemoryQuizHistoryStore


def _valid_responses_by_task() -> dict[str, str]:
    quiz_questions = [
        {
            "question": "What is CDC in data systems?",
            "options": [
                "Capturing row-level DB changes as events",
                "Compressing static snapshots only",
                "Replacing all ETL with batch jobs",
                "A UI charting standard",
            ],
            "correct_option_index": 0,
        },
        {
            "question": "Why is log-based CDC preferred?",
            "options": [
                "It always rewrites schema",
                "It minimizes source DB overhead",
                "It requires no ordering guarantees",
                "It only works for NoSQL",
            ],
            "correct_option_index": 1,
        },
        {
            "question": "What does a broker provide in CDC architecture?",
            "options": [
                "Durable transport and fan-out",
                "Primary key generation",
                "SQL query optimization",
                "Database backups",
            ],
            "correct_option_index": 0,
        },
    ]
    audio_dialogue = [
        {"speaker": "Ava", "text": "CDC captures row-level changes continuously."},
        {"speaker": "Noah", "text": "That keeps downstream systems near real-time."},
        {"speaker": "Ava", "text": "The broker preserves durable ordered streams."},
        {"speaker": "Noah", "text": "Processors can enrich and route events safely."},
        {"speaker": "Ava", "text": "Sinks consume updates without polling full tables."},
        {"speaker": "Noah", "text": "This reduces latency and improves consistency."},
        {"speaker": "Ava", "text": "Ordering helps prevent stale writes downstream."},
        {"speaker": "Noah", "text": "Schema evolution needs explicit compatibility rules."},
        {"speaker": "Ava", "text": "Backpressure controls protect consumers during spikes."},
        {"speaker": "Noah", "text": "Monitoring lag and retries keeps pipelines healthy."},
    ]
    video_dialogue = [
        {"speaker": "Ava", "text": "This slide introduces the key CDC concept."},
        {"speaker": "Noah", "text": "We capture commits and publish ordered events."},
        {"speaker": "Ava", "text": "That enables near real-time downstream updates."},
    ]

    return {
        "topic_explainer": "CDC Pipeline is an event-driven data synchronization pattern.",
        "mindmap_graph": _json(
            {
                "name": "CDC Pipeline",
                "children": [
                    {"name": "Capture", "children": []},
                    {"name": "Transport", "children": []},
                ],
            }
        ),
        "flashcards_generate": _json(
            {
                "topic": "CDC Pipeline",
                "cards": [
                    {
                        "question": "What does CDC stand for?",
                        "short_answer": "Change Data Capture.",
                    },
                    {
                        "question": "Why use CDC?",
                        "short_answer": "To deliver low-latency data changes downstream.",
                    },
                ],
            }
        ),
        "data_table_generate": _json(
            {
                "topic": "CDC Pipeline",
                "columns": ["Subtype", "Latency", "Complexity"],
                "rows": [
                    {
                        "Subtype": "Log-based CDC",
                        "Latency": "Low",
                        "Complexity": "Medium",
                    },
                    {
                        "Subtype": "Trigger-based CDC",
                        "Latency": "Medium",
                        "Complexity": "High",
                    },
                    {
                        "Subtype": "Timestamp polling",
                        "Latency": "Higher",
                        "Complexity": "Low",
                    },
                ],
            }
        ),
        "quiz_generate": _json({"topic": "CDC Pipeline", "questions": quiz_questions}),
        "slideshow_outline": _json(
            {
                "topic": "CDC Pipeline",
                "subtopics": [
                    {"title": "Architecture", "focus": "Core building blocks"},
                    {"title": "Operations", "focus": "Monitoring and reliability"},
                ],
            }
        ),
        "slideshow_section": _json(
            {
                "slides": [
                    {
                        "title": "CDC Section Slide",
                        "bullets": [
                            "Capture changes from source transactions.",
                            "Publish ordered events to a durable stream.",
                        ],
                        "speaker_notes": "Keep this operational and practical.",
                        "code_snippet": "",
                        "code_language": "",
                    }
                ]
            }
        ),
        "audio_overview_script": _json(
            {
                "topic": "CDC Pipeline",
                "title": "CDC Overview",
                "speakers": [
                    {"name": "Ava", "role": "Host"},
                    {"name": "Noah", "role": "Engineer"},
                ],
                "dialogue": audio_dialogue,
                "summary": "CDC keeps systems synchronized with low latency.",
            }
        ),
        "video_slide_script": _json(
            {
                "topic": "CDC Pipeline",
                "title": "Slide Narration",
                "speakers": [
                    {"name": "Ava", "role": "Guide"},
                    {"name": "Noah", "role": "Engineer"},
                ],
                "dialogue": video_dialogue,
                "summary": "Narration summary.",
            }
        ),
        "report_generate_briefing_doc": (
            "# CDC Pipeline Briefing\n\n"
            "## Executive Summary\n"
            "CDC delivers reliable low-latency propagation of source changes."
        ),
    }


def _error_responses_by_task() -> dict[str, str]:
    return {
        "mindmap_graph": "not json",
        "flashcards_generate": "not json",
        "data_table_generate": "not json",
        "quiz_generate": "not json",
        "slideshow_outline": "not json",
        "audio_overview_script": "not json",
    }


def _asset_payloads() -> dict[str, dict[str, Any]]:
    return {
        "topic": {
            "topic": "CDC Pipeline",
            "additional_instructions": "Include implementation trade-offs.",
        },
        "mindmap": {
            "topic": "CDC Pipeline",
            "max_depth": 3,
            "constraints": "Keep concise.",
        },
        "flashcards": {
            "topic": "CDC Pipeline",
            "card_count": 5,
            "constraints": "Interview focused.",
        },
        "data table": {
            "topic": "CDC Pipeline",
            "row_count": 4,
            "notes": "Compare capture approaches.",
        },
        "quiz": {
            "topic": "CDC Pipeline",
            "question_count": 3,
            "difficulty": "Intermediate",
            "constraints": "Practical architecture questions.",
        },
        "slideshow": {
            "topic": "CDC Pipeline",
            "constraints": "Keep concise.",
            "subtopic_count": 2,
            "slides_per_subtopic": 1,
            "code_mode": "none",
            "representation_mode": "auto",
        },
        "video": {
            "topic": "CDC Pipeline",
            "constraints": "Keep concise.",
            "subtopic_count": 2,
            "slides_per_subtopic": 1,
            "code_mode": "none",
            "representation_mode": "auto",
            "speaker_count": 2,
            "conversation_style": "Educational Discussion",
            "language": "en",
            "slow_audio": False,
            "video_template": "standard",
            "animation_style": "smooth",
            "youtube_prompt": False,
        },
        "audio_overview": {
            "topic": "CDC Pipeline",
            "speaker_count": 2,
            "turn_count": 6,
            "conversation_style": "Educational Discussion",
            "constraints": "Practical tone.",
            "language": "en",
            "slow_audio": False,
            "youtube_prompt": False,
        },
        "report": {
            "topic": "CDC Pipeline",
            "format_key": "briefing_doc",
            "additional_notes": "Focus on production readiness.",
        },
    }


def _build_harness(llm_service: _ScriptedLLMService) -> _FlowHarness:
    asset_history = AssetHistoryService(store=_InMemoryAssetHistoryStore())  # type: ignore[arg-type]
    quiz_history_store = _InMemoryQuizHistoryStore()

    mind_map_service = MindMapService(
        llm_service=llm_service,  # type: ignore[arg-type]
        parser=MindMapParser(llm_service),  # type: ignore[arg-type]
        history_service=asset_history,
    )
    flashcards_service = FlashcardsService(
        llm_service=llm_service,  # type: ignore[arg-type]
        parser=FlashcardsParser(llm_service),  # type: ignore[arg-type]
        history_service=asset_history,
    )
    data_table_service = DataTableService(
        llm_service=llm_service,  # type: ignore[arg-type]
        parser=DataTableParser(llm_service),  # type: ignore[arg-type]
        history_service=asset_history,
    )
    quiz_service = QuizService(
        llm_service=llm_service,  # type: ignore[arg-type]
        parser=QuizParser(llm_service),  # type: ignore[arg-type]
        history_store=quiz_history_store,  # type: ignore[arg-type]
        asset_history_service=asset_history,
    )
    slideshow_service = SlideShowService(
        llm_service=llm_service,  # type: ignore[arg-type]
        parser=SlideShowParser(llm_service),  # type: ignore[arg-type]
        history_service=asset_history,
    )
    audio_parser = AudioOverviewParser(llm_service)  # type: ignore[arg-type]
    audio_service = AudioOverviewService(
        llm_service=llm_service,  # type: ignore[arg-type]
        parser=audio_parser,
        history_service=asset_history,
    )
    audio_service.synthesize_mp3 = lambda **_kwargs: (b"audio-bytes", None)  # type: ignore[method-assign]

    video_service = VideoAssetService(
        llm_service=llm_service,  # type: ignore[arg-type]
        slideshow_service=slideshow_service,
        script_parser=audio_parser,
        audio_overview_service=audio_service,
        history_service=asset_history,
    )
    video_service.synthesize_audio = lambda **_kwargs: (b"video-audio-bytes", None)  # type: ignore[method-assign]

    explainer_service = TopicExplainerService(
        llm_service=llm_service,  # type: ignore[arg-type]
        history_service=asset_history,
    )
    report_service = ReportService(
        llm_service=llm_service,  # type: ignore[arg-type]
        history_service=asset_history,
    )

    registry = build_default_asset_executor_registry(
        explainer_service=explainer_service,
        mind_map_service=mind_map_service,
        flashcards_service=flashcards_service,
        data_table_service=data_table_service,
        quiz_service=quiz_service,
        slideshow_service=slideshow_service,
        video_service=video_service,
        audio_overview_service=audio_service,
        report_service=report_service,
    )

    intent_router = IntentRouterService(
        llm_service=llm_service,  # type: ignore[arg-type]
        parser=IntentParser(),
    )
    dashboard = AgentDashboardService(
        intent_router=intent_router,
        explainer_service=explainer_service,
        mind_map_service=mind_map_service,
        flashcards_service=flashcards_service,
        data_table_service=data_table_service,
        quiz_service=quiz_service,
        slideshow_service=slideshow_service,
        video_service=video_service,
        audio_overview_service=audio_service,
        report_service=report_service,
        asset_executor_registry=registry,
    )

    return _FlowHarness(
        registry=registry,
        dashboard=dashboard,
        asset_history_service=asset_history,
        quiz_history_store=quiz_history_store,
    )


class TestIntegrationFullFlows(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = GroqSettings(
            api_key="test-key",
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=1024,
        )
        self.settings_without_llm = GroqSettings(
            api_key="",
            model="",
            temperature=0.2,
            max_tokens=512,
        )

    def test_each_asset_happy_path_via_registry(self) -> None:
        llm = _ScriptedLLMService(responses_by_task=_valid_responses_by_task())
        harness = _build_harness(llm)
        payloads = _asset_payloads()

        for intent, payload in payloads.items():
            with self.subTest(intent=intent):
                result = harness.registry.execute(
                    intent=intent,
                    payload=payload,  # type: ignore[arg-type]
                    settings=self.settings,
                )
                self.assertEqual(result.status, "success")
                self.assertEqual(result.intent, intent)
                self.assertFalse(result.error)

        self.assertEqual(len(harness.asset_history_service.list_records()), len(payloads))
        self.assertEqual(len(harness.quiz_history_store.list_quizzes()), 1)

    def test_each_asset_error_path_via_registry(self) -> None:
        llm = _ScriptedLLMService(
            responses_by_task=_error_responses_by_task(),
            errors_by_task={
                "topic_explainer": RuntimeError("Topic generation failed."),
                "report_generate_briefing_doc": RuntimeError("Report generation failed."),
            },
        )
        harness = _build_harness(llm)
        payloads = _asset_payloads()

        for intent, payload in payloads.items():
            with self.subTest(intent=intent):
                result = harness.registry.execute(
                    intent=intent,
                    payload=payload,  # type: ignore[arg-type]
                    settings=self.settings,
                )
                self.assertEqual(result.status, "error")
                self.assertTrue(result.error)

    def test_agent_dashboard_end_to_end_happy_path(self) -> None:
        llm = _ScriptedLLMService(responses_by_task=_valid_responses_by_task())
        harness = _build_harness(llm)

        plan, notes, error, _ = harness.dashboard.plan_from_message(
            message=(
                'Create topic, mindmap, flashcards, data table, quiz, slideshow, '
                'video, audio overview, and report about "CDC Pipeline".'
            ),
            planner_mode=IntentRouterService.MODE_LOCAL_FIRST,
            settings=self.settings,
            active_topic="",
        )

        self.assertIsNone(error)
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(
            plan.intents,
            [
                "topic",
                "mindmap",
                "flashcards",
                "data table",
                "quiz",
                "slideshow",
                "video",
                "audio_overview",
                "report",
            ],
        )
        self.assertTrue(any("Intent detected locally" in note for note in notes))

        assets, generation_notes = harness.dashboard.generate_assets_from_plan(
            plan=plan,
            settings=self.settings,
        )
        self.assertEqual(len(assets), 9)
        self.assertTrue(all(asset.status == "success" for asset in assets))
        self.assertTrue(any("Generated 9/9 assets" in note for note in generation_notes))
        self.assertEqual(
            harness.dashboard.extract_primary_topic_from_assets(assets),
            "CDC Pipeline",
        )

    def test_agent_dashboard_end_to_end_missing_topic_error_path(self) -> None:
        llm = _ScriptedLLMService(responses_by_task=_valid_responses_by_task())
        harness = _build_harness(llm)

        plan, _, error, _ = harness.dashboard.plan_from_message(
            message="Create a mindmap and quiz please.",
            planner_mode=IntentRouterService.MODE_LOCAL_FIRST,
            settings=self.settings_without_llm,
            active_topic="",
        )
        self.assertIsNone(error)
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.intents, ["mindmap", "quiz"])
        self.assertEqual(plan.missing_mandatory["mindmap"], ["topic"])
        self.assertEqual(plan.missing_mandatory["quiz"], ["topic"])

        missing_prompt = harness.dashboard.format_missing_mandatory_question(plan)
        self.assertIn("Please provide the topic", missing_prompt)

        errored_assets, _ = harness.dashboard.generate_assets_from_plan(
            plan=plan,
            settings=self.settings,
        )
        self.assertTrue(all(asset.status == "error" for asset in errored_assets))
        self.assertTrue(
            all("Mandatory requirements missing" in asset.error for asset in errored_assets)
        )

        updated_plan, _, reply_error, _ = harness.dashboard.apply_mandatory_reply(
            plan=plan,
            user_reply="Topic: CDC Pipeline",
            settings=self.settings_without_llm,
        )
        self.assertIsNone(reply_error)
        self.assertEqual(updated_plan.missing_mandatory["mindmap"], [])
        self.assertEqual(updated_plan.missing_mandatory["quiz"], [])

        recovered_assets, _ = harness.dashboard.generate_assets_from_plan(
            plan=updated_plan,
            settings=self.settings,
        )
        self.assertTrue(all(asset.status == "success" for asset in recovered_assets))

    def test_verify_failure_blocks_dependency_chain(self) -> None:
        llm = _ScriptedLLMService(responses_by_task=_valid_responses_by_task())
        harness = _build_harness(llm)

        def _bad_slideshow_executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            return AgentAssetResult(
                intent="slideshow",
                status="success",
                payload=payload,
                content={"slides": []},
                title="Slide Show: CDC Pipeline",
            )

        harness.registry.register("slideshow", _bad_slideshow_executor)

        plan = AgentPlan(
            source_message="Create slideshow and video for CDC Pipeline",
            planner_mode="local_first",
            intents=["slideshow", "video"],
            payloads={
                "slideshow": {
                    "topic": "CDC Pipeline",
                    "constraints": "Keep concise.",
                    "subtopic_count": 2,
                    "slides_per_subtopic": 1,
                    "code_mode": "none",
                },
                "video": {
                    "topic": "CDC Pipeline",
                    "constraints": "Keep concise.",
                    "subtopic_count": 2,
                    "slides_per_subtopic": 1,
                    "code_mode": "none",
                    "speaker_count": 2,
                    "conversation_style": "Educational Discussion",
                    "language": "en",
                    "slow_audio": False,
                    "video_template": "standard",
                    "animation_style": "smooth",
                    "youtube_prompt": False,
                },
            },
            missing_mandatory={"slideshow": [], "video": []},
            missing_optional={"slideshow": [], "video": []},
        )

        assets, notes = harness.dashboard.generate_assets_from_plan(plan=plan, settings=self.settings)
        self.assertEqual(len(assets), 2)
        slideshow_asset = next(asset for asset in assets if asset.intent == "slideshow")
        video_asset = next(asset for asset in assets if asset.intent == "video")
        self.assertEqual(slideshow_asset.status, "error")
        self.assertIn("Verification failed", slideshow_asset.error)
        self.assertEqual(video_asset.status, "error")
        self.assertIn("Missing required dependency artifacts", video_asset.error)
        self.assertTrue(any("verify_result" in note for note in notes))

    def test_transient_execute_retry_recovers(self) -> None:
        old_retry = os.environ.get("EXECUTE_RETRY_COUNT")
        os.environ["EXECUTE_RETRY_COUNT"] = "1"
        try:
            llm = _ScriptedLLMService(responses_by_task=_valid_responses_by_task())
            harness = _build_harness(llm)
            state = {"count": 0}

            def _flaky_topic_executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
                state["count"] += 1
                if state["count"] == 1:
                    return AgentAssetResult(intent="topic", status="error", payload=payload, error="temporary fail")
                return AgentAssetResult(
                    intent="topic",
                    status="success",
                    payload=payload,
                    content="This is a sufficiently long description for verification to pass cleanly.",
                )

            harness.registry.register("topic", _flaky_topic_executor)
            plan = AgentPlan(
                source_message="Explain CDC",
                planner_mode="local_first",
                intents=["topic"],
                payloads={"topic": {"topic": "CDC Pipeline"}},
                missing_mandatory={"topic": []},
                missing_optional={"topic": []},
            )
            assets, notes = harness.dashboard.generate_assets_from_plan(plan=plan, settings=self.settings)
            self.assertEqual(len(assets), 1)
            self.assertEqual(assets[0].status, "success")
            self.assertTrue(any("attempt=2" in note for note in notes))
        finally:
            if old_retry is None:
                os.environ.pop("EXECUTE_RETRY_COUNT", None)
            else:
                os.environ["EXECUTE_RETRY_COUNT"] = old_retry

    def test_execute_timeout_returns_timeout_error_code(self) -> None:
        old_timeout = os.environ.get("EXECUTE_STAGE_TIMEOUT_MS")
        os.environ["EXECUTE_STAGE_TIMEOUT_MS"] = "1"
        try:
            llm = _ScriptedLLMService(responses_by_task=_valid_responses_by_task())
            harness = _build_harness(llm)

            def _slow_topic_executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
                import time

                time.sleep(0.003)
                return AgentAssetResult(
                    intent="topic",
                    status="success",
                    payload=payload,
                    content="This is a sufficiently long description for verification to pass cleanly.",
                )

            harness.registry.register("topic", _slow_topic_executor)
            plan = AgentPlan(
                source_message="Explain CDC",
                planner_mode="local_first",
                intents=["topic"],
                payloads={"topic": {"topic": "CDC Pipeline"}},
                missing_mandatory={"topic": []},
                missing_optional={"topic": []},
            )
            assets, _ = harness.dashboard.generate_assets_from_plan(plan=plan, settings=self.settings)
            self.assertEqual(len(assets), 1)
            self.assertEqual(assets[0].status, "error")
            artifact = assets[0].artifact if isinstance(assets[0].artifact, dict) else {}
            sections = artifact.get("sections", []) if isinstance(artifact.get("sections"), list) else []
            self.assertTrue(
                any(
                    isinstance(section, dict)
                    and isinstance(section.get("data"), dict)
                    and str(section.get("data", {}).get("code", "")).strip() == "E_STAGE_TIMEOUT"
                    for section in sections
                )
            )
        finally:
            if old_timeout is None:
                os.environ.pop("EXECUTE_STAGE_TIMEOUT_MS", None)
            else:
                os.environ["EXECUTE_STAGE_TIMEOUT_MS"] = old_timeout


if __name__ == "__main__":
    unittest.main()
