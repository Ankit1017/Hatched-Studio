from __future__ import annotations

import streamlit as st

from main_app.services.background_jobs import BackgroundJobManager


def render_background_job_panel(
    *,
    manager: BackgroundJobManager,
    job_id: str,
    title: str,
    key_prefix: str,
    allow_retry: bool = True,
) -> str:
    normalized_job_id = " ".join(str(job_id).split()).strip()
    if not normalized_job_id:
        return ""

    snapshot = manager.get_snapshot(normalized_job_id)
    if snapshot is None:
        st.warning("Background job state not found. Start a new generation request.")
        return ""

    with st.container(border=True):
        st.markdown(f"#### {title}")
        st.caption(f"Job ID: `{snapshot.id}`")

        status = snapshot.status.replace("_", " ").title()
        queue_note = ""
        if snapshot.queue_position is not None:
            queue_note = f" | Queue position: {snapshot.queue_position}"
        st.caption(f"Status: {status} | Progress: {int(snapshot.progress * 100)}%{queue_note}")
        st.progress(float(snapshot.progress), text=snapshot.message or status)

        if snapshot.error:
            st.error(snapshot.error)

        if snapshot.retry_of:
            st.caption(f"Retry of job `{snapshot.retry_of}`")

        button_col_1, button_col_2, button_col_3 = st.columns([0.33, 0.33, 0.34], gap="small")
        with button_col_1:
            if snapshot.is_active:
                if st.button("Cancel", key=f"{key_prefix}_cancel", width="stretch"):
                    manager.cancel(snapshot.id)
                    st.info("Cancellation requested.")
                    st.rerun()
            else:
                st.button(
                    "Cancel",
                    key=f"{key_prefix}_cancel_disabled",
                    width="stretch",
                    disabled=True,
                )
        with button_col_2:
            if st.button("Refresh Status", key=f"{key_prefix}_refresh", width="stretch"):
                st.rerun()
        with button_col_3:
            if allow_retry and snapshot.is_terminal:
                if st.button("Retry Job", key=f"{key_prefix}_retry", width="stretch"):
                    new_job_id = manager.retry(snapshot.id)
                    if new_job_id:
                        st.success("Retry queued in background.")
                        return new_job_id
                    st.warning("Retry is not available for this job.")
            else:
                st.button(
                    "Retry Job",
                    key=f"{key_prefix}_retry_disabled",
                    width="stretch",
                    disabled=True,
                )

    return normalized_job_id
