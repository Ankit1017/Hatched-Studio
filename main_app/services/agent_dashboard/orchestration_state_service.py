from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from main_app.contracts import OrchestrationState
from main_app.services.agent_dashboard.error_codes import E_STATE_TRANSITION_INVALID


@dataclass(frozen=True)
class TransitionResult:
    from_state: OrchestrationState
    to_state: OrchestrationState
    valid: bool
    error_code: str = ""
    message: str = ""


class OrchestrationStateService:
    _ALLOWED: dict[OrchestrationState, set[OrchestrationState]] = {
        "pending": {"ready", "blocked", "skipped"},
        "ready": {"running", "blocked", "skipped"},
        "running": {"completed", "failed"},
        "blocked": {"ready", "skipped"},
        "completed": set(),
        "failed": set(),
        "skipped": set(),
    }

    def can_transition(self, *, from_state: OrchestrationState, to_state: OrchestrationState) -> bool:
        return to_state in self._ALLOWED.get(from_state, set())

    def transition(self, *, from_state: OrchestrationState, to_state: OrchestrationState) -> TransitionResult:
        if self.can_transition(from_state=from_state, to_state=to_state):
            return TransitionResult(from_state=from_state, to_state=to_state, valid=True)
        return TransitionResult(
            from_state=from_state,
            to_state=to_state,
            valid=False,
            error_code=E_STATE_TRANSITION_INVALID,
            message=f"Invalid orchestration state transition `{from_state}` -> `{to_state}`.",
        )

    def recalculate_blocked(
        self,
        *,
        dependencies: dict[str, set[str]],
        terminal_failed: Iterable[str],
        current_states: dict[str, OrchestrationState],
    ) -> dict[str, OrchestrationState]:
        failed = set(terminal_failed)
        next_states = dict(current_states)
        for node, parents in dependencies.items():
            if next_states.get(node) in {"completed", "failed", "skipped"}:
                continue
            if any(parent in failed for parent in parents):
                next_states[node] = "blocked"
        return next_states
