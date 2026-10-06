import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _resolve(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    anthropic_api_key: str
    anthropic_model: str
    gemini_api_key: str
    gemini_model: str

    tts_provider: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    elevenlabs_model_id: str
    google_tts_api_key: str
    google_tts_language_code: str
    google_tts_voice_name: str

    vm_base_url: str
    vm_secret: str
    vm_timeout_seconds: int
    raw_video_path: str
    output_filename: str

    youtube_client_secret_file: Path
    youtube_token_file: Path
    youtube_privacy_status: str
    youtube_category_id: str
    youtube_default_tags: list[str]

    topics_file: Path
    scripts_dir: Path
    voiceover_dir: Path
    final_dir: Path
    thumbnail_path: str

    cron_days: list[str]
    cron_time: str
    webhook_host: str
    webhook_port: int
    webhook_secret: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "anthropic").strip().lower(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest").strip(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro").strip(),
            tts_provider=os.getenv("TTS_PROVIDER", "elevenlabs").strip().lower(),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", "").strip(),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "").strip(),
            elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip(),
            google_tts_api_key=os.getenv("GOOGLE_TTS_API_KEY", "").strip(),
            google_tts_language_code=os.getenv("GOOGLE_TTS_LANGUAGE_CODE", "hi-IN").strip(),
            google_tts_voice_name=os.getenv("GOOGLE_TTS_VOICE_NAME", "").strip(),
            vm_base_url=os.getenv("VM_BASE_URL", "http://127.0.0.1:5000").strip().rstrip("/"),
            vm_secret=os.getenv("VM_SECRET", "").strip(),
            vm_timeout_seconds=int(os.getenv("VM_TIMEOUT_SECONDS", "1800")),
            raw_video_path=os.getenv(
                "RAW_VIDEO_PATH", "/opt/sketch_spark_engine/output/raw_notebooklm_video.mp4"
            ).strip(),
            output_filename=os.getenv("OUTPUT_FILENAME", "chintu_magical_breakfast_final.mp4").strip(),
            youtube_client_secret_file=_resolve(
                os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "credentials/client_secret.json")
            ),
            youtube_token_file=_resolve(os.getenv("YOUTUBE_TOKEN_FILE", "credentials/token.json")),
            youtube_privacy_status=os.getenv("YOUTUBE_PRIVACY_STATUS", "private").strip().lower(),
            youtube_category_id=os.getenv("YOUTUBE_CATEGORY_ID", "24").strip(),
            youtube_default_tags=_csv(
                os.getenv(
                    "YOUTUBE_DEFAULT_TAGS",
                    "chintu,hindi cartoon,tech cartoon,notebooklm",
                )
            ),
            topics_file=_resolve(os.getenv("TOPICS_FILE", "data/topics.json")),
            scripts_dir=_resolve(os.getenv("SCRIPTS_DIR", "output/scripts")),
            voiceover_dir=_resolve(os.getenv("VOICEOVER_DIR", "output/voiceovers")),
            final_dir=_resolve(os.getenv("FINAL_DIR", "output/final")),
            thumbnail_path=os.getenv("THUMBNAIL_PATH", "").strip(),
            cron_days=[day.lower() for day in _csv(os.getenv("CRON_DAYS", "monday,thursday"))],
            cron_time=os.getenv("CRON_TIME", "10:00").strip(),
            webhook_host=os.getenv("WEBHOOK_HOST", "0.0.0.0").strip(),
            webhook_port=int(os.getenv("WEBHOOK_PORT", "8080")),
            webhook_secret=os.getenv("WEBHOOK_SECRET", "").strip(),
        )
