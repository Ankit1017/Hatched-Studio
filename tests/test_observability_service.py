from __future__ import annotations

import unittest

from main_app.infrastructure.groq_client import CompletionResult, CompletionUsage
from main_app.services.cached_llm_service import CachedLLMService
from main_app.services.observability_service import (
    ObservabilityService,
    clear_request_id,
    get_request_id,
)
from main_app.models import GroqSettings


class _FakeCacheStore:
    def __init__(self) -> None:
        self.saved_payloads: list[dict[str, object]] = []

    def load(self) -> dict[str, object]:
        return {}

    def save(self, data: dict[str, object]) -> None:
        self.saved_payloads.append(dict(data))


class _FakeMetadataChatClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete_with_metadata(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        messages: list[dict[str, str]],
    ) -> CompletionResult:
        del api_key, model, temperature, max_tokens, messages
        self.calls += 1
        return CompletionResult(
            text='{"ok": true}',
            usage=CompletionUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500),
        )

    def complete(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        messages: list[dict[str, str]],
    ) -> str:
        del api_key, model, temperature, max_tokens, messages
        self.calls += 1
        return '{"ok": true}'


class TestObservabilityService(unittest.TestCase):
    def setUp(self) -> None:
        clear_request_id()

    def test_cached_llm_tracks_per_asset_metrics_and_cost(self) -> None:
        observability = ObservabilityService(
            default_input_cost_per_1m_usd=1.0,
            default_output_cost_per_1m_usd=2.0,
        )
        cache_store = _FakeCacheStore()
        llm_service = CachedLLMService(
            chat_client=_FakeMetadataChatClient(),
            cache_store=cache_store,
            cache_data={},
            observability_service=observability,
        )
        settings = GroqSettings(
            api_key="test-key",
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=700,
        )
        messages = [{"role": "user", "content": "Explain CDC pipeline"}]

        raw_1, hit_1 = llm_service.call(
            settings=settings,
            messages=messages,
            task="topic_explainer",
            label="Explainer: CDC",
            topic="CDC Pipeline",
        )
        raw_2, hit_2 = llm_service.call(
            settings=settings,
            messages=messages,
            task="topic_explainer",
            label="Explainer: CDC",
            topic="CDC Pipeline",
        )

        self.assertEqual(raw_1, '{"ok": true}')
        self.assertEqual(raw_2, '{"ok": true}')
        self.assertFalse(hit_1)
        self.assertTrue(hit_2)

        rows = observability.metrics_table_rows()
        topic_rows = [row for row in rows if row.get("asset") == "topic"]
        self.assertEqual(len(topic_rows), 1)
        topic_row = topic_rows[0]
        self.assertEqual(topic_row["llm_calls"], 2)
        self.assertEqual(topic_row["cache_hits"], 1)
        self.assertGreater(topic_row["avg_latency_ms"], 0.0)
        self.assertEqual(topic_row["total_tokens"], 3000)
        self.assertAlmostEqual(topic_row["est_cost_usd"], 0.002, places=6)
        self.assertTrue(topic_row["last_request_id"].startswith("req_"))
        self.assertTrue(get_request_id().startswith("req_"))

    def test_asset_resolution_for_known_and_unknown_tasks(self) -> None:
        observability = ObservabilityService()
        self.assertEqual(observability.resolve_asset_name("quiz_generate"), "quiz")
        self.assertEqual(observability.resolve_asset_name("report_generate_blog_post"), "report")
        self.assertEqual(observability.resolve_asset_name("agent_general_chat"), "agent_chat")
        self.assertEqual(observability.resolve_asset_name("something_unmapped"), "other")


if __name__ == "__main__":
    unittest.main()
