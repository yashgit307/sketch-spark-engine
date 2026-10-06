import json
import logging
import re
import time
from pathlib import Path

from . import script_gen, tts, uploader, vm_client
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


def run_pipeline(topic: str | None = None, publish: bool = True, settings: Settings | None = None) -> dict:
    settings = settings or Settings.from_env()
    entry = {"topic": topic} if topic else _next_entry(settings)
    topic_text = str(entry.get("topic", "")).strip()
    if not topic_text:
        raise ValueError("No topic provided")

    log.info("Pipeline start | topic: %s", topic_text)
    slug = _slug(topic_text)

    script = script_gen.generate_script(topic_text, settings)
    settings.scripts_dir.mkdir(parents=True, exist_ok=True)
    script_file = settings.scripts_dir / f"{slug}.json"
    script_file.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    voiceover_file = settings.voiceover_dir / f"{slug}.mp3"
    tts.synthesize(script["narration"], voiceover_file, settings)

    output_filename = entry.get("output_filename") or settings.output_filename
    vm_result = vm_client.dispatch_video(
        settings.raw_video_path, voiceover_file, output_filename, settings
    )

    result = {
        "topic": topic_text,
        "script_file": str(script_file),
        "voiceover_file": str(voiceover_file),
        "vm": vm_result,
        "youtube": None,
    }

    if publish:
        local_video = vm_client.download_file(output_filename, settings.final_dir, settings)
        thumbnail_value = entry.get("thumbnail_path") or settings.thumbnail_path
        thumbnail_file = Path(thumbnail_value) if thumbnail_value else None
        result["youtube"] = uploader.upload_video(local_video, script, thumbnail_file, settings)
        result["final_video"] = str(local_video)

    log.info("Pipeline finished: %s", json.dumps(result, ensure_ascii=False, default=str))
    return result
