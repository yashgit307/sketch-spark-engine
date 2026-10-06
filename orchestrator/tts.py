import base64
import logging
import re
from pathlib import Path

import requests

from .config import Settings

log = logging.getLogger(__name__)

ELEVENLABS_MAX_CHARS = 3000
GOOGLE_MAX_CHARS = 900


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[।!?])\s+|(?<=\.)\s+|(?<=\?)\s+", normalized)
    return [part.strip() for part in parts if part.strip()]


def _chunks(text: str, limit: int) -> list[str]:
    chunks: list[str] = []
    buffer = ""
    for sentence in _sentences(text):
        if len(sentence) > limit:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(sentence[i : i + limit] for i in range(0, len(sentence), limit))
            continue
        candidate = f"{buffer} {sentence}".strip()
        if len(candidate) > limit:
            chunks.append(buffer)
            buffer = sentence
        else:
            buffer = candidate
    if buffer:
        chunks.append(buffer)
    return chunks


def _elevenlabs(text: str, settings: Settings) -> bytes:
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        raise RuntimeError("ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID must be set")
    parts: list[bytes] = []
    for chunk in _chunks(text, ELEVENLABS_MAX_CHARS):
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
            headers={
                "xi-api-key": settings.elevenlabs_api_key,
                "content-type": "application/json",
                "accept": "audio/mpeg",
            },
            json={
                "text": chunk,
                "model_id": settings.elevenlabs_model_id,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=120,
        )
        response.raise_for_status()
        parts.append(response.content)
    return b"".join(parts)


def _google(text: str, settings: Settings) -> bytes:
    if not settings.google_tts_api_key:
        raise RuntimeError("GOOGLE_TTS_API_KEY must be set")
    voice: dict = {"languageCode": settings.google_tts_language_code}
    if settings.google_tts_voice_name:
        voice["name"] = settings.google_tts_voice_name
    parts: list[bytes] = []
    for chunk in _chunks(text, GOOGLE_MAX_CHARS):
        response = requests.post(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            params={"key": settings.google_tts_api_key},
            json={
                "input": {"text": chunk},
                "voice": voice,
                "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.0},
            },
            timeout=60,
        )
        response.raise_for_status()
        parts.append(base64.b64decode(response.json()["audioContent"]))
    return b"".join(parts)


PROVIDERS = {"elevenlabs": _elevenlabs, "google": _google}


def synthesize(text: str, output_path: Path, settings: Settings) -> Path:
    provider = PROVIDERS.get(settings.tts_provider)
    if provider is None:
        raise ValueError(f"Unknown TTS_PROVIDER '{settings.tts_provider}' (use elevenlabs|google)")
    if not text.strip():
        raise ValueError("Narration text is empty")
    log.info("Synthesizing voiceover via %s (%d chars)", settings.tts_provider, len(text))
    audio = provider(text, settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio)
    log.info("Voiceover written: %s (%.1f KB)", output_path, len(audio) / 1024)
    return output_path
