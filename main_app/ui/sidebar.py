from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from main_app.constants import PRESET_MODELS
from main_app.models import GroqSettings
from main_app.services.cached_llm_service import CachedLLMService
from main_app.services.observability_service import ObservabilityService


@dataclass
class SidebarRenderResult:
    settings: GroqSettings
    cache_count_placeholder: Any


def render_sidebar(
    *,
    llm_service: CachedLLMService,
    cache_location: str,
    observability_service: ObservabilityService | None = None,
) -> SidebarRenderResult:
    with st.sidebar:
        st.header("Groq Configuration")

        api_key = st.text_input("Groq API Key", type="password", help="Your Groq API key.")

        model_mode = st.radio("Model Selection", ["Pick from list", "Custom model ID"], horizontal=False)
        if model_mode == "Pick from list":
            model = st.selectbox("Model", PRESET_MODELS)
        else:
            model = st.text_input("Custom Model ID", placeholder="e.g. llama-3.3-70b-versatile")

        temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.4, step=0.1)
        max_tokens = st.number_input("Max Output Tokens", min_value=128, max_value=8192, value=1400, step=64)

        st.divider()
        st.subheader("Cache")
        cache_count_placeholder = st.empty()
        cache_count_placeholder.caption(f"Cached responses: {llm_service.count}")
        st.caption(f"Cache storage: {cache_location}")

        cache_keys = llm_service.cache_keys_latest_first()
        if cache_keys:
            selected_cache_key = st.selectbox(
                "Select Cached Entry",
                options=cache_keys,
                format_func=llm_service.cache_entry_label,
            )
            if st.button("Clear Selected Cache Entry"):
                llm_service.clear_entry(selected_cache_key)
                st.success("Selected cache entry cleared.")
                st.rerun()

        if st.button("Clear LLM Cache"):
            llm_service.clear_all()
            st.success("LLM cache cleared.")
            st.rerun()

        if observability_service is not None:
            st.divider()
            st.subheader("Observability")
            current_request_id = observability_service.current_request_id()
            if current_request_id:
                st.caption(f"Current request ID: `{current_request_id}`")
            else:
                st.caption("Current request ID: (none yet)")

            overall = observability_service.overall_metrics()
            st.caption(
                (
                    f"LLM calls: {overall.llm_calls} | "
                    f"Cache hit rate: {overall.cache_hit_rate * 100:.2f}% | "
                    f"Avg latency: {overall.avg_latency_ms:.2f} ms | "
                    f"Est. cost: ${overall.total_estimated_cost_usd:.6f}"
                )
            )

            metrics_rows = observability_service.metrics_table_rows()
            if metrics_rows:
                st.dataframe(metrics_rows, width="stretch", hide_index=True)
            else:
                st.caption("No LLM metrics recorded yet.")

            if st.button("Reset Observability Metrics", key="reset_observability_metrics"):
                observability_service.reset()
                st.success("Observability metrics reset.")
                st.rerun()

        st.caption("Tip: lower temperature is more factual; higher gives more variation.")

    settings = GroqSettings(
        api_key=api_key,
        model=model,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
    )
    return SidebarRenderResult(settings=settings, cache_count_placeholder=cache_count_placeholder)
