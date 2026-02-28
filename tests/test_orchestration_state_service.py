from __future__ import annotations

import unittest

from main_app.services.agent_dashboard.orchestration_state_service import OrchestrationStateService


class TestOrchestrationStateService(unittest.TestCase):
    def test_valid_transition(self) -> None:
        service = OrchestrationStateService()
        result = service.transition(from_state="pending", to_state="ready")
        self.assertTrue(result.valid)

    def test_invalid_transition(self) -> None:
        service = OrchestrationStateService()
        result = service.transition(from_state="completed", to_state="running")
        self.assertFalse(result.valid)
        self.assertEqual(result.error_code, "E_STATE_TRANSITION_INVALID")


if __name__ == "__main__":
    unittest.main()
