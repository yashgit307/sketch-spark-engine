import json
import logging
import re
import time
from pathlib import Path

from . import script_gen, status, tts, uploader, vm_client, social_publisher
from .config import Settings

log = logging.getLogger(__name__)


def _slug(text: str) -> str:
    slug = re.sub(r"[^\w\u0900-\u097F]+", "-", text.lower()).strip("-")
    return slug[:60] or f"video-{int(time.time())}"


def _next_entry(settings: Settings) -> dict:
    if not settings.topics_file.exists():
        raise FileNotFoundError(
            f"Topics file not found: {settings.topics_file}. "
            "Create it as a JSON array of topics."
        )
    queue = json.loads(settings.topics_file.read_text(encoding="utf-8"))
    if not queue:
        raise RuntimeError(f"Topic queue is empty: {settings.topics_file}")
    entry = queue.pop(0)
    settings.topics_file.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"topic": entry} if isinstance(entry, str) else entry


def run_pipeline(
    topic: str | None = None,
    platforms: list[str] | None = None,
    settings: Settings | None = None
) -> dict:
    settings = settings or Settings.from_env()
    entry = {"topic": topic} if topic else _next_entry(settings)
    topic_text = str(entry.get("topic", "")).strip()
    if not topic_text:
        raise ValueError("No topic provided")

    log.info("Pipeline start | topic: %s", topic_text)
    slug = _slug(topic_text)
    status.start_episode(settings, slug, topic_text)

    try:
        script = script_gen.generate_script(topic_text, settings)
        settings.scripts_dir.mkdir(parents=True, exist_ok=True)
        script_file = settings.scripts_dir / f"{slug}.json"
        script_file.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
        status.mark_stage(settings, slug, "script", script_file.name)

        voiceover_file = settings.voiceover_dir / f"{slug}.mp3"
        tts.synthesize(script["narration"], voiceover_file, settings)
        status.mark_stage(settings, slug, "tts", voiceover_file.name)

        output_filename = entry.get("output_filename") or settings.output_filename
        vm_result = vm_client.dispatch_video(
            settings.raw_video_path, voiceover_file, output_filename, settings
        )
        status.mark_stage(settings, slug, "render", output_filename)

        result = {
            "topic": topic_text,
            "script_file": str(script_file),
            "voiceover_file": str(voiceover_file),
            "vm": vm_result,
            "youtube": None,
            "instagram": None,
            "pinterest": None,
        }

        platforms = [p.lower() for p in (platforms or ["youtube"])]
        if "all" in platforms:
            platforms = ["youtube", "instagram", "pinterest"]

        if platforms:
            local_video = vm_client.download_file(output_filename, settings.final_dir, settings)
            status.mark_stage(settings, slug, "download", local_video.name)
            thumbnail_value = entry.get("thumbnail_path") or settings.thumbnail_path
            thumbnail_file = Path(thumbnail_value) if thumbnail_value else None
            result["final_video"] = str(local_video)

            if "youtube" in platforms:
                result["youtube"] = uploader.upload_video(local_video, script, thumbnail_file, settings)
                status.mark_stage(
                    settings, slug, "publish_youtube", result["youtube"].get("video_id", "")
                )
            
            if "instagram" in platforms:
                result["instagram"] = social_publisher.publish_to_instagram(local_video, script, settings)
                status.mark_stage(settings, slug, "publish_instagram", result["instagram"].get("status", ""))
                
            if "pinterest" in platforms:
                result["pinterest"] = social_publisher.publish_to_pinterest(local_video, script, settings)
                status.mark_stage(settings, slug, "publish_pinterest", result["pinterest"].get("status", ""))

    except Exception as exc:
        status.finish_episode(settings, slug, ok=False, detail=str(exc))
        log.exception("Pipeline failed for %s", topic_text)
        raise

    status.finish_episode(settings, slug, ok=True)
    log.info("Pipeline finished: %s", json.dumps(result, ensure_ascii=False, default=str))
    return result
