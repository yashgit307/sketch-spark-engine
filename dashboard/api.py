import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from orchestrator import channels, status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402


def settings() -> Settings:
    return Settings.from_env()


def vm_health(cfg: Settings) -> dict:
    return _vm_get(cfg, "/health")


def vm_stats(cfg: Settings) -> dict:
    return _vm_get(cfg, "/stats")


def vm_jobs(cfg: Settings) -> dict:
    return _vm_get(cfg, "/jobs")


def _vm_headers(cfg: Settings) -> dict:
    headers = {}
    if cfg.vm_secret:
        headers["X-VM-Secret"] = cfg.vm_secret
    return headers


def _vm_get(cfg: Settings, endpoint: str) -> dict:
    response = requests.get(
        f"{cfg.vm_base_url}{endpoint}",
        headers=_vm_headers(cfg),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def pipeline_status(cfg: Settings) -> list[dict]:
    return status.load(cfg)


def topics_queue(cfg: Settings) -> list:
    path = cfg.topics_file
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def youtube_channels(cfg: Settings):
    return channels.list_channels(cfg)


def run_episode(cfg: Settings, topic: str = "", publish: bool = True, platforms: list = None, account_creds: dict = None):
    import subprocess
    import os

    command = [sys.executable, "-m", "orchestrator", "run"]
    if topic:
        command += ["--topic", topic]
    if not publish:
        command.append("--no-publish")
    elif platforms:
        command += ["--platform", ",".join(platforms)]
        
    env = os.environ.copy()
    if account_creds:
        for k, v in account_creds.items():
            if v:
                env[k] = str(v)

    return subprocess.Popen(command, cwd=str(ROOT), env=env)