import json

import streamlit as st

from api import (
    pipeline_status,
    run_episode,
    settings,
    topics_queue,
    vm_health,
    vm_jobs,
    vm_stats,
    youtube_channels,
)

st.set_page_config(page_title="Chintu Pipeline Console", layout="wide")
st.title("Chintu Pipeline Console")

cfg = settings()

with st.sidebar:
    st.subheader("Configuration")
    st.write(f"VM endpoint: `{cfg.vm_base_url}`")
    st.write(f"VM secret set: `{bool(cfg.vm_secret)}`")
    st.write(f"YouTube credentials: `{cfg.youtube_client_secret_file.name or cfg.youtube_token_file.name}`")
    st.write(f"Privacy: `{cfg.youtube_privacy_status}` | Category: `{cfg.youtube_category_id}`")
    st.write(f"Schedule: `{', '.join(cfg.cron_days)} at {cfg.cron_time}`")
    if st.button("Refresh", use_container_width=True):
        st.rerun()

tab_vm, tab_episodes, tab_youtube, tab_settings = st.tabs(
    ["VM", "Episodes", "YouTube", "Settings"]
)

with tab_vm:
    try:
        health = vm_health(cfg)
        st.subheader("Health")
        st.write(health)
    except Exception as exc:
        st.error(f"VM unreachable: {exc}")

    try:
        stats = vm_stats(cfg)
        st.subheader("VM at a glance")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Hostname", stats["hostname"])
        col2.metric("Uptime", f"{stats['uptime_seconds'] // 3600}h {stats['uptime_seconds'] % 3600 // 60}m")
        col3.metric("Active renders", stats["active_jobs"])
        col4.metric("FFmpeg", stats["ffmpeg"].replace("ffmpeg version ", "").split(" ")[0])
        st.subheader("Disk usage")
        disk = stats["disk"]
        st.progress(disk["used"] / disk["total"])
        st.write(
            f"{disk['used'] / 1e9:.1f} GB used / {disk['free'] / 1e9:.1f} GB free / "
            f"{disk['total'] / 1e9:.1f} GB total"
        )
        st.caption(f"Output directory: `{disk['output_dir']}`")
    except Exception as exc:
        st.warning(f"Could not load VM stats: {exc}")

    try:
        jobs = vm_jobs(cfg)
        st.subheader("Active renders")
        st.table(
            [
                {
                    "id": row["id"],
                    "output": row["output_filename"],
                    "started": row["started_at"],
                    "raw": row["raw_video_path"],
                }
                for row in jobs["active"]
            ]
        )
        st.subheader("Recent renders")
        st.table(
            [
                {
                    "id": row["id"],
                    "output": row["output_filename"],
                    "status": row["status"],
                    "started": row["started_at"],
                    "finished": row["finished_at"],
                    "message": row["message"],
                }
                for row in jobs["recent"]
            ]
        )
    except Exception as exc:
        st.warning(f"Could not load render jobs: {exc}")

with tab_episodes:
    st.subheader("Episode pipeline statuses")
    episodes = pipeline_status(cfg)
    if not episodes:
        st.info("No episodes tracked yet. Run the pipeline once to populate this view.")
    st.table(
        [
            {
                "slug": episode["slug"],
                "topic": episode["topic"],
                "status": episode.get("status", ""),
                "last_stage": episode.get("last_stage", ""),
                "updated": episode.get("updated_at", ""),
                "message": episode.get("message", ""),
            }
            for episode in episodes
        ]
    )

    st.subheader("Topic queue")
    queue = topics_queue(cfg)
    if not queue:
        st.info("Topic queue is empty.")
    st.code(json.dumps(queue, ensure_ascii=False, indent=2) if queue else "[]")

    st.subheader("Trigger a run")
    publish = st.checkbox("Publish to YouTube after render", value=True)
    col1, col2 = st.columns(2)
    if col1.button("Run next queued topic", use_container_width=True):
        run_episode(cfg, publish=publish)
        st.success("Pipeline started in the background. Refresh to watch it progress.")
    with col2.popover("Run a specific topic"):
        topic = st.text_input("Topic text")
        if st.button("Start"):
            if topic.strip():
                run_episode(cfg, topic=topic.strip(), publish=publish)
                st.success(f"Started: {topic}")
            else:
                st.warning("Enter a topic first.")

with tab_youtube:
    st.subheader("Connected YouTube channels")
    try:
        channels = youtube_channels(cfg)
        if not channels:
            st.info("No channels found on this account.")
        st.table(
            [
                {
                    "title": channel["title"],
                    "handle": channel["custom_url"],
                    "subscribers": channel["subscribers"],
                    "videos": channel["video_count"],
                    "views": channel["view_count"],
                    "published": channel["published_at"],
                    "uploads_playlist": channel["uploads_playlist"],
                }
                for channel in channels
            ]
        )
    except Exception as exc:
        st.warning(
            f"Could not list channels: {exc}. "
            f"Ensure client_secret.json exists at `{cfg.youtube_client_secret_file}` "
            "and grant consent once so token.json is created."
        )

with tab_settings:
    st.subheader("Effective settings (secrets masked)")
    masked = {
        "LLM_PROVIDER": cfg.llm_provider,
        "LLM_MODEL": cfg.anthropic_model if cfg.llm_provider == "anthropic" else cfg.gemini_model,
        "TTS_PROVIDER": cfg.tts_provider,
        "VM_BASE_URL": cfg.vm_base_url,
        "VM_SECRET": "***" if cfg.vm_secret else "",
        "RAW_VIDEO_PATH": cfg.raw_video_path,
        "OUTPUT_FILENAME": cfg.output_filename,
        "YOUTUBE_PRIVACY_STATUS": cfg.youtube_privacy_status,
        "YOUTUBE_CATEGORY_ID": cfg.youtube_category_id,
        "TOPICS_FILE": str(cfg.topics_file),
        "THUMBNAIL_PATH": cfg.thumbnail_path,
        "CRON_DAYS": ",".join(cfg.cron_days),
        "CRON_TIME": cfg.cron_time,
        "WEBHOOK_PORT": cfg.webhook_port,
        "WEBHOOK_SECRET": "***" if cfg.webhook_secret else "",
    }
    st.json(masked)