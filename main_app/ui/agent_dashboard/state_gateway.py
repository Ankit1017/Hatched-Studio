from __future__ import annotations

from typing import Any, MutableMapping, Protocol


class SessionStateGateway(Protocol):
    def get(self, key: str, default: Any = None) -> Any:
        ...

    def set(self, key: str, value: Any) -> None:
        ...

    def setdefault(self, key: str, default: Any) -> Any:
        ...


class StreamlitSessionStateGateway:
    def __init__(self, state: MutableMapping[str, Any] | None = None) -> None:
        if state is not None:
            self._state = state
            return

        try:
            import streamlit as st  # type: ignore
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "StreamlitSessionStateGateway requires streamlit when no explicit state mapping is provided."
            ) from exc
        self._state = st.session_state

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._state[key] = value

    def setdefault(self, key: str, default: Any) -> Any:
        return self._state.setdefault(key, default)
