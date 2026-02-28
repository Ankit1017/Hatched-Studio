from __future__ import annotations

import csv
from dataclasses import dataclass
from html import escape
import io
import random
import re
from typing import Any, Callable

import streamlit as st

from main_app.models import GroqSettings
from main_app.services.cached_llm_service import CachedLLMService
from main_app.services.flashcards_service import FlashcardsService


FlashcardExplainFn = Callable[[str, str, str, int], tuple[str, bool]]


@dataclass(frozen=True)
class FlashcardsRenderConfig:
    state_index_key: str
    state_show_answer_key: str
    state_explanations_key: str
    prev_button_key: str
    next_button_key: str
    see_answer_button_key_format: str
    explain_button_key_format: str
    restart_button_key: str
    shuffle_button_key: str
    download_csv_key: str


def render_flashcards_view(
    *,
    topic: str,
    cards: list[dict[str, Any]],
    settings: GroqSettings,
    config: FlashcardsRenderConfig,
    explain_fn: FlashcardExplainFn,
    llm_service: CachedLLMService,
    cache_count_placeholder: Any,
    title: str = "Agent Flashcards",
    subtitle: str | None = None,
) -> None:
    if not cards:
        st.warning("No flashcards available.")
        return

    total_cards = len(cards)
    subtitle_text = subtitle or f"Based on {total_cards} generated cards"

    if config.state_index_key not in st.session_state:
        st.session_state[config.state_index_key] = 0
    if config.state_show_answer_key not in st.session_state:
        st.session_state[config.state_show_answer_key] = False
    if config.state_explanations_key not in st.session_state or not isinstance(
        st.session_state[config.state_explanations_key],
        dict,
    ):
        st.session_state[config.state_explanations_key] = {}

    current_index = int(st.session_state[config.state_index_key])
    if current_index < 0 or current_index >= total_cards:
        current_index = 0
        st.session_state[config.state_index_key] = 0
        st.session_state[config.state_show_answer_key] = False

    current_card = cards[current_index] if isinstance(cards[current_index], dict) else {}
    showing_answer = bool(st.session_state[config.state_show_answer_key])

    question = str(current_card.get("question", "")).strip()
    short_answer = str(current_card.get("short_answer", "")).strip()
    display_text_raw = short_answer if showing_answer else question
    display_text = FlashcardsService.sanitize_card_text(display_text_raw)
    card_mode = "answer" if showing_answer else "question"

    st.markdown(
        f"""
        <div class="flashdeck-header">
            <div>
                <div class="flashdeck-title">{escape(title)}</div>
                <div class="flashdeck-subtitle">{escape(subtitle_text)}</div>
            </div>
            <div class="flashdeck-topic-badge">{escape(topic)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav_left_col, card_col, nav_right_col = st.columns([1, 5, 1], vertical_alignment="center")
    with nav_left_col:
        prev_clicked = st.button("←", key=config.prev_button_key, width="stretch")
    with nav_right_col:
        next_clicked = st.button("→", key=config.next_button_key, width="stretch")

    if prev_clicked:
        st.session_state[config.state_index_key] = (current_index - 1) % total_cards
        st.session_state[config.state_show_answer_key] = False
        st.rerun()
    if next_clicked:
        st.session_state[config.state_index_key] = (current_index + 1) % total_cards
        st.session_state[config.state_show_answer_key] = False
        st.rerun()

    with card_col:
        card_markup = (
            '<div class="flashdeck-stage">'
            '<div class="flashdeck-card-shadow-1"></div>'
            '<div class="flashdeck-card-shadow-2"></div>'
            f'<div class="flashdeck-card-main {card_mode}">'
            f'<div class="flashdeck-card-text">{escape(display_text)}</div>'
            "</div></div>"
        )
        st.markdown(card_markup, unsafe_allow_html=True)

        explain_clicked = False
        card_action_cols = st.columns([0.22, 0.56, 0.22])
        if not showing_answer:
            if card_action_cols[1].button(
                "See Answer",
                key=config.see_answer_button_key_format.format(index=current_index),
                width="stretch",
            ):
                st.session_state[config.state_show_answer_key] = True
                st.rerun()
        else:
            explain_clicked = card_action_cols[1].button(
                "Explain",
                key=config.explain_button_key_format.format(index=current_index),
                width="stretch",
            )

        utility_col_1, utility_col_2, utility_col_3, utility_col_4 = st.columns([0.12, 0.2, 0.5, 0.18])
        if utility_col_1.button("↻", key=config.restart_button_key, width="stretch"):
            st.session_state[config.state_index_key] = 0
            st.session_state[config.state_show_answer_key] = False
            st.rerun()
        if utility_col_2.button("Shuffle", key=config.shuffle_button_key, width="stretch"):
            if total_cards > 1:
                candidate_indices = [idx for idx in range(total_cards) if idx != current_index]
                st.session_state[config.state_index_key] = random.choice(candidate_indices)
            else:
                st.session_state[config.state_index_key] = 0
            st.session_state[config.state_show_answer_key] = False
            st.rerun()

        progress_percent = (float(current_index + 1) / float(total_cards)) * 100.0
        utility_col_3.markdown(
            f"""
            <div class="flashdeck-progress-wrap">
                <div class="flashdeck-progress-track">
                    <div class="flashdeck-progress-fill" style="width: {progress_percent:.2f}%;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        utility_col_4.markdown(
            f'<div class="flashdeck-count">{current_index + 1} / {total_cards} cards</div>',
            unsafe_allow_html=True,
        )

        csv_bytes = _flashcards_to_csv_bytes(topic=topic, cards=cards)
        safe_topic = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic.strip())[:60].strip("_") or "flashcards"
        st.download_button(
            "Download Flashcards (CSV)",
            data=csv_bytes,
            file_name=f"{safe_topic}_flashcards.csv",
            mime="text/csv",
            key=config.download_csv_key,
            width="stretch",
        )

        if explain_clicked:
            if not settings.has_api_key():
                st.error("Please enter your Groq API key in the sidebar.")
            elif not settings.has_model():
                st.error("Please select or enter a valid model.")
            else:
                try:
                    with st.spinner("Generating detailed explanation..."):
                        explanation_text, cache_hit = explain_fn(
                            topic,
                            question,
                            short_answer,
                            current_index,
                        )
                    st.session_state[config.state_explanations_key][current_index] = explanation_text
                    if cache_hit:
                        st.info("Explanation served from cache.")
                    else:
                        cache_count_placeholder.caption(f"Cached responses: {llm_service.count}")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Explanation request failed: {exc}")

    explanations = st.session_state[config.state_explanations_key]
    if current_index in explanations:
        st.markdown("---")
        st.subheader(f"Detailed Explanation (Card {current_index + 1})")
        st.markdown(str(explanations[current_index]))


def _flashcards_to_csv_bytes(*, topic: str, cards: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    fieldnames = ["Card Number", "Topic", "Question", "Short Answer"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for idx, card in enumerate(cards, start=1):
        if not isinstance(card, dict):
            continue
        writer.writerow(
            {
                "Card Number": idx,
                "Topic": str(topic).strip(),
                "Question": str(card.get("question", "")).strip(),
                "Short Answer": str(card.get("short_answer", "")).strip(),
            }
        )
    return buffer.getvalue().encode("utf-8")
