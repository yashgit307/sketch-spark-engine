import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings

log = logging.getLogger(__name__)


def status_file(settings: Settings) -> Path:
    return settings.topics_file.parent / "pipeline_status.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        log.exception("Unable to read pipeline status %s", path)
        return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _entry(data: dict, slug: str, topic: str) -> dict:
    entry = data.setdefault(
        slug,
        {
            "slug": slug,
            "topic": topic,
            "started_at": _iso_now(),
            "stages": {},
            "status": "running",
            "updated_at": _iso_now(),
        },
    )
    entry.setdefault("slug", slug)
    entry.setdefault("topic", topic)
    entry.setdefault("stages", {})
    entry.setdefault("started_at", _iso_now())
    entry.setdefault("status", "running")
    return entry


def start_episode(settings: Settings, slug: str, topic: str) -> None:
    path = status_file(settings)
    data = _load(path)
    _entry(data, slug, topic)
    data[slug]["updated_at"] = _iso_now()
    _save(path, data)


def mark_stage(settings: Settings, slug: str, stage: str, detail: str = "") -> None:
    path = status_file(settings)
    data = _load(path)
    entry = _entry(data, slug, slug)
    entry["stages"][stage] = {"at": _iso_now(), "detail": detail}
    entry["last_stage"] = stage
    entry["updated_at"] = _iso_now()
    _save(path, data)


def finish_episode(settings: Settings, slug: str, ok: bool, detail: str = "") -> None:
    path = status_file(settings)
    data = _load(path)
    entry = data.setdefault(
        slug,
        {"slug": slug, "topic": slug, "started_at": _iso_now(), "stages": {}},
    )
    entry["status"] = "ok" if ok else "error"
    entry["finished_at"] = _iso_now()
    entry["message"] = detail
    entry["updated_at"] = _iso_now()
    _save(path, data)


def load(settings: Settings) -> list[dict]:
    data = _load(status_file(settings))
    episodes = list(data.values())
    episodes.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return episodes