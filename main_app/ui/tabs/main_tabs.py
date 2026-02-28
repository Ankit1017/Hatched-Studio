from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import streamlit as st

from main_app.infrastructure.agent_dashboard_session_store import AgentDashboardSessionRepository
from main_app.services.agent_dashboard import AgentDashboardService
from main_app.services.asset_history_service import AssetHistoryService
from main_app.services.audio_overview_service import AudioOverviewService
from main_app.services.background_jobs import BackgroundJobManager
from main_app.services.cached_llm_service import CachedLLMService
from main_app.services.data_table_service import DataTableService
from main_app.services.flashcards_service import FlashcardsService
from main_app.services.intent import IntentRouterService
from main_app.services.mind_map_service import MindMapService
from main_app.services.quiz_exporter import QuizExporter
from main_app.services.quiz_service import QuizService
from main_app.services.report_exporter import ReportExporter
from main_app.services.report_service import ReportService
from main_app.services.slide_deck_exporter import SlideDeckExporter
from main_app.services.slideshow_service import SlideShowService
from main_app.services.source_grounding_service import SourceGroundingService
from main_app.domains.topic.services.topic_explainer_service import TopicExplainerService
from main_app.services.video_asset_service import VideoAssetService
from main_app.services.video_exporter import VideoExporter
from main_app.models import GroqSettings
from main_app.ui.tabs.agent_dashboard_tab import render_agent_dashboard_tab
from main_app.ui.tabs.asset_history_tab import render_asset_history_tab
from main_app.ui.tabs.audio_overview_tab import render_audio_overview_tab
from main_app.ui.tabs.data_table_tab import render_data_table_tab
from main_app.ui.tabs.explainer_tab import render_explainer_tab
from main_app.ui.tabs.flashcards_tab import render_flashcards_tab
from main_app.ui.tabs.intent_chat_tab import render_intent_chat_tab
from main_app.ui.tabs.mind_map_tab import render_mind_map_tab
from main_app.ui.tabs.quiz_tab import render_quiz_tab
from main_app.ui.tabs.report_tab import render_report_tab
from main_app.ui.tabs.slideshow_tab import render_slideshow_tab
from main_app.ui.tabs.video_tab import render_video_tab


@dataclass(frozen=True)
class TabRegistration:
    title: str
    render: Callable[[], None]


def build_main_tab_registrations(
    *,
    explainer_service: TopicExplainerService,
    mind_map_service: MindMapService,
    flashcards_service: FlashcardsService,
    report_service: ReportService,
    data_table_service: DataTableService,
    quiz_service: QuizService,
    slideshow_service: SlideShowService,
    video_service: VideoAssetService,
    audio_overview_service: AudioOverviewService,
    intent_router_service: IntentRouterService,
    agent_dashboard_service: AgentDashboardService,
    asset_history_service: AssetHistoryService,
    llm_service: CachedLLMService,
    settings: GroqSettings,
    cache_count_placeholder: Any,
    agent_dashboard_session_store: AgentDashboardSessionRepository,
    quiz_exporter: QuizExporter,
    report_exporter: ReportExporter,
    slide_exporter: SlideDeckExporter,
    video_exporter: VideoExporter,
    job_manager: BackgroundJobManager,
    source_grounding_service: SourceGroundingService,
) -> list[TabRegistration]:
    return [
        TabRegistration(
            title="Detailed Description",
            render=lambda: render_explainer_tab(
                explainer_service=explainer_service,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
                source_grounding_service=source_grounding_service,
            ),
        ),
        TabRegistration(
            title="Mind Map Builder",
            render=lambda: render_mind_map_tab(
                mind_map_service=mind_map_service,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
            ),
        ),
        TabRegistration(
            title="Flashcards",
            render=lambda: render_flashcards_tab(
                flashcards_service=flashcards_service,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
            ),
        ),
        TabRegistration(
            title="Create Report",
            render=lambda: render_report_tab(
                report_service=report_service,
                report_exporter=report_exporter,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
                source_grounding_service=source_grounding_service,
            ),
        ),
        TabRegistration(
            title="Data Table",
            render=lambda: render_data_table_tab(
                data_table_service=data_table_service,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
            ),
        ),
        TabRegistration(
            title="Quiz",
            render=lambda: render_quiz_tab(
                quiz_service=quiz_service,
                quiz_exporter=quiz_exporter,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
                source_grounding_service=source_grounding_service,
            ),
        ),
        TabRegistration(
            title="Slide Show",
            render=lambda: render_slideshow_tab(
                slideshow_service=slideshow_service,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
                slide_exporter=slide_exporter,
                job_manager=job_manager,
                source_grounding_service=source_grounding_service,
            ),
        ),
        TabRegistration(
            title="Video Builder",
            render=lambda: render_video_tab(
                video_service=video_service,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
                slide_exporter=slide_exporter,
                video_exporter=video_exporter,
                job_manager=job_manager,
            ),
        ),
        TabRegistration(
            title="Audio Overview",
            render=lambda: render_audio_overview_tab(
                audio_overview_service=audio_overview_service,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
                job_manager=job_manager,
            ),
        ),
        TabRegistration(
            title="Chat Bot Intent",
            render=lambda: render_intent_chat_tab(
                intent_router_service=intent_router_service,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
            ),
        ),
        TabRegistration(
            title="Agent Dashboard",
            render=lambda: render_agent_dashboard_tab(
                agent_dashboard_service=agent_dashboard_service,
                llm_service=llm_service,
                settings=settings,
                cache_count_placeholder=cache_count_placeholder,
                session_store=agent_dashboard_session_store,
                quiz_exporter=quiz_exporter,
                report_exporter=report_exporter,
                slide_exporter=slide_exporter,
                video_service=video_service,
                video_exporter=video_exporter,
            ),
        ),
        TabRegistration(
            title="Asset History",
            render=lambda: render_asset_history_tab(
                asset_history_service=asset_history_service,
                settings=settings,
                llm_service=llm_service,
                cache_count_placeholder=cache_count_placeholder,
                agent_dashboard_service=agent_dashboard_service,
                audio_overview_service=audio_overview_service,
                video_service=video_service,
                quiz_exporter=quiz_exporter,
                report_exporter=report_exporter,
                slide_exporter=slide_exporter,
                video_exporter=video_exporter,
            ),
        ),
    ]


def render_main_tabs(registrations: list[TabRegistration]) -> None:
    tab_titles = [registration.title for registration in registrations]
    tab_containers = st.tabs(tab_titles)
    for container, registration in zip(tab_containers, registrations):
        with container:
            registration.render()
