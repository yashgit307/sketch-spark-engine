import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobRegistry:
    def __init__(self, store: Path, keep: int = 200):
        self.store = store
        self.keep = keep
        self._lock = threading.RLock()
        self._records: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.store.exists():
            return
        try:
            data = json.loads(self.store.read_text(encoding="utf-8"))
            self._records = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            log.exception("Unable to read jobs file %s", self.store)
            self._records = []

    def _save(self) -> None:
        try:
            self.store.parent.mkdir(parents=True, exist_ok=True)
            temp = self.store.with_suffix(".tmp")
            temp.write_text(
                json.dumps(self._records, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temp.replace(self.store)
        except OSError:
            log.exception("Unable to persist jobs file %s", self.store)

    def start(self, output_filename: str, raw_video_path: str, voiceover_path: str) -> str:
        record = {
            "id": f"job-{int(time.time() * 1000)}",
            "output_filename": output_filename,
            "raw_video_path": raw_video_path,
            "voiceover_path": voiceover_path,
            "status": "running",
            "started_at": _iso_now(),
            "finished_at": "",
            "message": "",
        }
        with self._lock:
            self._records.append(record)
            self._save()
        log.info("Job started: %s", record["id"])
        return record["id"]

    def finish(self, job_id: str, ok: bool, message: str = "") -> None:
        with self._lock:
            for record in self._records:
                if record["id"] == job_id:
                    record["status"] = "ok" if ok else "error"
                    record["finished_at"] = _iso_now()
                    record["message"] = message
                    break
            self._records = self._records[-self.keep :]
            self._save()
        log.info("Job finished: %s ok=%s", job_id, ok)

    def active(self) -> list[dict]:
        with self._lock:
            return [record for record in self._records if record["status"] == "running"]

    def recent(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return [dict(record) for record in self._records[-limit:]][::-1]