import logging
from pathlib import Path
from urllib.parse import quote

import requests

from .config import Settings

log = logging.getLogger(__name__)

UPLOAD_CHUNK = 1024 * 1024


def _headers(settings: Settings) -> dict:
    headers = {"Content-Type": "application/json"}
    if settings.vm_secret:
        headers["X-VM-Secret"] = settings.vm_secret
    return headers


def upload_file(local_path: Path, settings: Settings) -> str:
    headers = {}
    if settings.vm_secret:
        headers["X-VM-Secret"] = settings.vm_secret
    log.info("Uploading %s to VM", local_path)
    with open(local_path, "rb") as handle:
        response = requests.post(
            f"{settings.vm_base_url}/upload",
            files={"file": (local_path.name, handle)},
            headers=headers,
            timeout=settings.vm_timeout_seconds,
        )
    response.raise_for_status()
    remote_path = response.json()["path"]
    log.info("VM stored file at %s", remote_path)
    return remote_path


def resolve_vm_path(path_value: str, settings: Settings) -> str:
    local = Path(path_value).expanduser()
    if local.is_file():
        return upload_file(local, settings)
    return path_value


def dispatch_video(
    raw_video_path: str,
    voiceover_path: Path | str,
    output_filename: str,
    settings: Settings,
) -> dict:
    payload = {
        "raw_video_path": resolve_vm_path(raw_video_path, settings),
        "voiceover_path": resolve_vm_path(str(voiceover_path), settings),
        "output_filename": Path(output_filename).name,
    }
    log.info("Dispatching render job to %s/process-video", settings.vm_base_url)
    response = requests.post(
        f"{settings.vm_base_url}/process-video",
        json=payload,
        headers=_headers(settings),
        timeout=settings.vm_timeout_seconds,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("status") != "ok":
        raise RuntimeError(f"VM render failed: {result.get('message', result)}")
    log.info("VM render complete: %s", result.get("output_path"))
    return result


def download_file(filename: str, dest_dir: Path, settings: Settings) -> Path:
    headers = {}
    if settings.vm_secret:
        headers["X-VM-Secret"] = settings.vm_secret
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(filename).name
    url = f"{settings.vm_base_url}/download/{quote(dest.name)}"
    log.info("Downloading final video %s", dest.name)
    with requests.get(url, headers=headers, stream=True, timeout=settings.vm_timeout_seconds) as response:
        response.raise_for_status()
        with open(dest, "wb") as handle:
            for chunk in response.iter_content(chunk_size=UPLOAD_CHUNK):
                if chunk:
                    handle.write(chunk)
    log.info("Downloaded %s (%.1f MB)", dest, dest.stat().st_size / (1024 * 1024))
    return dest
