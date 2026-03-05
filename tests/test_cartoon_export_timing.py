from __future__ import annotations

import unittest

from main_app.services.cartoon_export_service import (
    _build_scene_timed_turns,
    _metadata_audio_segments,
    _mouth_for_time,
    _timed_turn_for_time,
)


class TestCartoonExportTiming(unittest.TestCase):
    def test_timed_turn_selection_uses_audio_segments(self) -> None:
        scene_turns = [
            {"turn_index": 0, "speaker_id": "ava", "text": "Intro"},
            {"turn_index": 1, "speaker_id": "noah", "text": "Follow up"},
        ]
        segments = _metadata_audio_segments(
            [
                {"segment_ref": "scene_01_turn_00", "start_ms": 1000, "end_ms": 1800, "text": "Intro"},
                {"segment_ref": "scene_01_turn_01", "start_ms": 1800, "end_ms": 2900, "text": "Follow up"},
            ]
        )
        timed_turns, scene_start = _build_scene_timed_turns(
            scene_turns=scene_turns,
            scene_index=1,
            scene_duration_ms=2500,
            audio_segments=segments,
            fallback_scene_start_ms=0,
        )

        self.assertEqual(scene_start, 1000)
        active = _timed_turn_for_time(timed_turns=timed_turns, time_ms=2200)
        assert active is not None
        self.assertEqual(active.turn.get("speaker_id"), "noah")

    def test_mouth_shape_uses_relative_cue_window(self) -> None:
        segment = {
            "segment_ref": "scene_01_turn_00",
            "start_ms": 1000,
            "end_ms": 2000,
            "mouth_cues": [
                {"start_ms": 0, "end_ms": 280, "mouth": "A"},
                {"start_ms": 280, "end_ms": 700, "mouth": "B"},
                {"start_ms": 700, "end_ms": 1000, "mouth": "X"},
            ],
        }

        self.assertEqual(_mouth_for_time(segment=segment, time_ms=1100), "A")
        self.assertEqual(_mouth_for_time(segment=segment, time_ms=1500), "B")
        self.assertEqual(_mouth_for_time(segment=segment, time_ms=1950), "X")


if __name__ == "__main__":
    unittest.main()
