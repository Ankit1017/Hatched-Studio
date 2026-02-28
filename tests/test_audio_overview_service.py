from __future__ import annotations

import sys
import types
import unittest

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[])))

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

from main_app.models import GroqSettings
from main_app.services.audio_overview_service import AudioOverviewService


class _FakeLLMService:
    def __init__(self) -> None:
        self.last_messages: list[dict[str, str]] = []

    def call(self, **kwargs: object) -> tuple[str, bool]:
        messages = kwargs.get("messages", [])
        if isinstance(messages, list):
            self.last_messages = [item for item in messages if isinstance(item, dict)]
        return '{"topic":"CDC","title":"t","speakers":[{"name":"Ava","role":"Host"},{"name":"Noah","role":"Engineer"}],"dialogue":[{"speaker":"Ava","text":"a"},{"speaker":"Noah","text":"b"},{"speaker":"Ava","text":"c"},{"speaker":"Noah","text":"d"},{"speaker":"Ava","text":"e"},{"speaker":"Noah","text":"f"}],"summary":"s"}', False


class _FakeParser:
    def parse(
        self,
        _raw_text: str,
        *,
        settings: GroqSettings,
        min_speakers: int,
        max_speakers: int,
        min_turns: int,
        max_turns: int,
    ) -> tuple[dict[str, object] | None, str | None, str | None]:
        del settings, min_speakers, max_speakers, min_turns, max_turns
        return {
            "topic": "CDC",
            "title": "CDC Overview",
            "speakers": [{"name": "Ava", "role": "Host"}, {"name": "Noah", "role": "Engineer"}],
            "dialogue": [
                {"speaker": "Ava", "text": "Turn 1"},
                {"speaker": "Noah", "text": "Turn 2"},
                {"speaker": "Ava", "text": "Turn 3"},
                {"speaker": "Noah", "text": "Turn 4"},
                {"speaker": "Ava", "text": "Turn 5"},
                {"speaker": "Noah", "text": "Turn 6"},
            ],
            "summary": "Summary",
        }, None, None


class TestAudioOverviewService(unittest.TestCase):
    def setUp(self) -> None:
        self.llm = _FakeLLMService()
        self.service = AudioOverviewService(
            llm_service=self.llm,
            parser=_FakeParser(),
            history_service=None,
        )
        self.settings = GroqSettings(
            api_key="test",
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=1024,
        )

    def _user_prompt(self) -> str:
        for message in self.llm.last_messages:
            if str(message.get("role", "")) == "user":
                return str(message.get("content", ""))
        return ""

    def test_generate_includes_youtube_prompt_block_when_enabled(self) -> None:
        result = self.service.generate(
            topic="CDC",
            speaker_count=2,
            turn_count=6,
            conversation_style="Educational Discussion",
            constraints="",
            use_youtube_prompt=True,
            settings=self.settings,
        )
        self.assertIsNone(result.parse_error)
        self.assertIn("Optional YouTube educational creator style", self._user_prompt())

    def test_generate_excludes_youtube_prompt_block_by_default(self) -> None:
        result = self.service.generate(
            topic="CDC",
            speaker_count=2,
            turn_count=6,
            conversation_style="Educational Discussion",
            constraints="",
            settings=self.settings,
        )
        self.assertIsNone(result.parse_error)
        self.assertNotIn("Optional YouTube educational creator style", self._user_prompt())


if __name__ == "__main__":
    unittest.main()
