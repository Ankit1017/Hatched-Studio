from __future__ import annotations

import streamlit as st

from main_app.ui.tabs.flashcards_tab import FLASHCARDS_CSS
from main_app.ui.tabs.quiz_tab import QUIZ_TAB_CSS
from main_app.ui.tabs.slideshow_tab import SLIDESHOW_TAB_CSS


AGENT_DASHBOARD_CSS = """
<style>
    .ad-title-wrap {
        border: 1px solid #dbe6f3;
        border-radius: 16px;
        background: linear-gradient(110deg, #f8fbff 0%, #f3f7ff 42%, #f8fbff 100%);
        padding: 14px 16px;
        margin: 4px 0 12px 0;
    }
    .ad-title {
        font-size: 1.78rem;
        font-weight: 760;
        color: #0f172a;
        margin: 0 0 2px 0;
        line-height: 1.2;
    }
    .ad-subtitle {
        color: #475569;
        margin: 0;
        font-size: 0.95rem;
        line-height: 1.4;
    }
    .ad-chip {
        display: inline-block;
        border: 1px solid #b6cdfb;
        background: #f2f7ff;
        color: #1a3c8b;
        border-radius: 999px;
        padding: 4px 11px;
        margin: 0 8px 8px 0;
        font-size: 0.8rem;
        font-weight: 630;
    }
    .ad-msg-row {
        display: flex;
        width: 100%;
        margin: 2px 0 4px 0;
    }
    .ad-msg-row-user {
        justify-content: flex-end;
    }
    .ad-msg-row-assistant {
        justify-content: flex-start;
    }
    .ad-msg-bubble {
        max-width: min(84%, 860px);
        border-radius: 16px;
        padding: 10px 13px;
        font-size: 0.97rem;
        line-height: 1.44;
        border: 1px solid transparent;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
        white-space: pre-wrap;
        overflow-wrap: break-word;
    }
    .ad-msg-bubble-user {
        background: linear-gradient(160deg, #2f5cff 0%, #3f67f9 100%);
        border-color: #2c53db;
        color: #ffffff;
        border-bottom-right-radius: 6px;
    }
    .ad-msg-bubble-assistant {
        background: #f8fafd;
        border-color: #dbe6f3;
        color: #0f172a;
        border-bottom-left-radius: 6px;
    }
    .ad-notes {
        border-left: 3px solid #d2e2ff;
        background: #f8fbff;
        color: #334155;
        border-radius: 0 10px 10px 0;
        padding: 8px 10px;
        margin: 4px 0 8px 0;
        font-size: 0.85rem;
        white-space: pre-line;
    }
    .ad-next-wrap {
        border: 1px dashed #b7c9eb;
        border-radius: 12px;
        background: #f8fbff;
        padding: 8px 10px 6px 10px;
        margin: 6px 0 10px 0;
    }
    .ad-next-title {
        margin: 0 0 6px 0;
        font-size: 0.84rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    .ad-next-item {
        margin: 0 0 6px 0;
        font-size: 0.88rem;
        color: #0f172a;
        line-height: 1.36;
    }
    .ad-next-intent {
        display: inline-block;
        border: 1px solid #c7d6f5;
        border-radius: 999px;
        background: #eef4ff;
        color: #233876;
        font-size: 0.76rem;
        padding: 2px 8px;
        margin: 0 6px 6px 0;
        font-weight: 600;
    }
    .ad-asset-card {
        border: 1px solid #dbe3ee;
        border-radius: 12px;
        background: #f9fbff;
        padding: 9px 11px;
        margin-bottom: 8px;
    }
    .ad-asset-title {
        margin: 0 0 4px 0;
        color: #0f172a;
        font-weight: 700;
    }
    .ad-asset-meta {
        margin: 0;
        color: #475569;
        font-size: 0.9rem;
    }
    div[data-testid="stChatMessage"] {
        padding-top: 0.05rem;
        padding-bottom: 0.05rem;
    }
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] > p {
        margin-bottom: 0.2rem;
    }
    div[data-testid="stChatInput"] {
        border-top: 1px solid #e3eaf5;
        padding-top: 10px;
        margin-top: 6px;
        background: linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(250,252,255,1) 20%);
    }
    [class*="st-key-agent_dashboard_flash_prev_"] button,
    [class*="st-key-agent_dashboard_flash_next_"] button {
        border-radius: 999px !important;
        width: 88px !important;
        height: 88px !important;
        border: 2px solid #3d5afe !important;
        color: #3d5afe !important;
        background: rgba(255, 255, 255, 0.78) !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        padding: 0 !important;
        min-height: 88px !important;
    }
    [class*="st-key-agent_dashboard_flash_restart_"] button {
        border-radius: 999px !important;
        width: 56px !important;
        height: 56px !important;
        min-height: 56px !important;
        border: 1px solid #cdd6e8 !important;
        background: #f8fafc !important;
        font-size: 1.25rem !important;
        font-weight: 600 !important;
    }
    [class*="st-key-agent_dashboard_flash_shuffle_"] button {
        border-radius: 999px !important;
        min-height: 48px !important;
        font-weight: 600 !important;
        border: 1px solid #c8d2e6 !important;
        background: #f8fafc !important;
        color: #111827 !important;
    }
    [class*="st-key-agent_dashboard_flash_show_"] {
        margin-top: -74px !important;
        position: relative;
        z-index: 25;
    }
    [class*="st-key-agent_dashboard_flash_show_"] button {
        border-radius: 999px !important;
        min-height: 48px !important;
        font-weight: 600 !important;
        background: #2f54ff !important;
        border: 1px solid #2f54ff !important;
        color: #ffffff !important;
    }
    [class*="st-key-agent_dashboard_flash_explain_"] {
        margin-top: -74px !important;
        position: relative;
        z-index: 25;
    }
    [class*="st-key-agent_dashboard_flash_explain_"] button {
        border-radius: 999px !important;
        min-height: 48px !important;
        font-weight: 600 !important;
        border: 1px solid #c8d2e6 !important;
        background: #f8fafc !important;
        color: #111827 !important;
    }
</style>
"""


def apply_agent_dashboard_styles() -> None:
    st.markdown(AGENT_DASHBOARD_CSS, unsafe_allow_html=True)
    st.markdown(FLASHCARDS_CSS, unsafe_allow_html=True)
    st.markdown(QUIZ_TAB_CSS, unsafe_allow_html=True)
    st.markdown(SLIDESHOW_TAB_CSS, unsafe_allow_html=True)
