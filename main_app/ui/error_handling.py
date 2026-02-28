from __future__ import annotations

import logging

import streamlit as st


logger = logging.getLogger(__name__)

UI_HANDLED_EXCEPTIONS = (
    AttributeError,
    KeyError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


def report_ui_error(*, action: str, exc: BaseException, prefix: str = "Request failed") -> None:
    logger.exception("UI action failed (%s): %s", action, exc)
    st.error(f"{prefix}: {exc}")


def report_ui_warning(*, action: str, exc: BaseException, prefix: str) -> None:
    logger.exception("UI warning fallback (%s): %s", action, exc)
    st.warning(f"{prefix}: {exc}")
