from __future__ import annotations

import unittest

from main_app.services.cartoon_motion_planner_service import CartoonMotionPlannerService


class TestCartoonMotionPlannerService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CartoonMotionPlannerService()
        self.scene = {
            "camera_track": {
                "keyframes": [
                    {"t_ms": 0, "x": 0.0, "y": 0.0, "zoom": 1.0, "rotation": 0.0, "ease": "linear"},
                    {"t_ms": 1000, "x": 100.0, "y": -10.0, "zoom": 1.2, "rotation": 5.0, "ease": "linear"},
                ]
            },
            "character_tracks": [
                {
                    "character_id": "ava",
                    "keyframes": [
                        {
                            "t_ms": 0,
                            "x_norm": 0.2,
                            "y_norm": 0.7,
                            "scale": 1.0,
                            "rotation": 0.0,
                            "pose": "idle",
                            "emotion": "neutral",
                            "opacity": 1.0,
                            "z_index": 1,
                            "ease": "linear",
                        },
                        {
                            "t_ms": 1000,
                            "x_norm": 0.6,
                            "y_norm": 0.7,
                            "scale": 1.2,
                            "rotation": 0.0,
                            "pose": "idle",
                            "emotion": "neutral",
                            "opacity": 1.0,
                            "z_index": 1,
                            "ease": "linear",
                        },
                    ],
                }
            ],
        }

    def test_plan_frame_interpolates_camera_and_character_track(self) -> None:
        plan = self.service.plan_frame(
            scene=self.scene,
            character_roster=[{"id": "ava", "name": "Ava"}],
            scene_relative_ms=500,
            scene_duration_ms=1000,
            active_turn={"speaker_id": "ava"},
            active_mouth="A",
        )
        camera = plan.get("camera", {})
        assert isinstance(camera, dict)
        self.assertAlmostEqual(float(camera.get("x", 0.0)), 50.0, delta=1.0)
        characters = plan.get("characters", [])
        assert isinstance(characters, list) and characters
        first = characters[0]
        assert isinstance(first, dict)
        self.assertAlmostEqual(float(first.get("x_norm", 0.0)), 0.4, delta=0.05)
        self.assertEqual(first.get("state"), "talk")
        self.assertEqual(first.get("viseme"), "A")
        self.assertNotEqual(str(first.get("pose", "idle")), "idle")

    def test_blink_precedence_over_talk(self) -> None:
        plan = self.service.plan_frame(
            scene=self.scene,
            character_roster=[{"id": "ava", "name": "Ava"}],
            scene_relative_ms=0,
            scene_duration_ms=1000,
            active_turn={"speaker_id": "ava"},
            active_mouth="E",
        )
        characters = plan.get("characters", [])
        assert isinstance(characters, list) and characters
        first = characters[0]
        assert isinstance(first, dict)
        self.assertEqual(first.get("state"), "blink")
        self.assertEqual(first.get("viseme"), "X")

    def test_secondary_motion_is_deterministic(self) -> None:
        args = {
            "scene": self.scene,
            "character_roster": [{"id": "ava", "name": "Ava"}],
            "scene_relative_ms": 640,
            "scene_duration_ms": 1000,
            "active_turn": {"speaker_id": "ava"},
            "active_mouth": "B",
        }
        first_plan = self.service.plan_frame(**args)
        second_plan = self.service.plan_frame(**args)
        first_chars = first_plan.get("characters", [])
        second_chars = second_plan.get("characters", [])
        assert isinstance(first_chars, list) and isinstance(second_chars, list) and first_chars and second_chars
        first_item = first_chars[0]
        second_item = second_chars[0]
        assert isinstance(first_item, dict) and isinstance(second_item, dict)
        first_motion = first_item.get("secondary_motion", {})
        second_motion = second_item.get("secondary_motion", {})
        self.assertEqual(first_motion, second_motion)
        assert isinstance(first_motion, dict)
        self.assertIn("torso_sway_px", first_motion)
        self.assertIn("head_nod_deg", first_motion)


if __name__ == "__main__":
    unittest.main()
