import json
import logging
import re

import requests

from .config import Settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the script engine of the Bigpikle automation pipeline, producing episodes of the "
    "'Chintu' Hindi tech cartoon series for a kids/family YouTube channel. Every video is "
    "self-declared made for kids: narration and visuals must be friendly, educational, "
    "age-appropriate, and free of scary, violent, or mature themes.\n"
    "Given a topic, return ONLY a valid JSON object (no markdown fences, no commentary) with exactly "
    "these keys:\n"
    '{"title": string - SEO YouTube title, max 90 chars, Hindi + searchable English keywords, '
    '"description": string - SEO description, 2-4 paragraphs, keywords in the first line, '
    "3-5 hashtags at the end, no made-for-kids restricted language, "
    '"tags": string[] - 10-15 SEO tags, '
    '"narration": string - complete Hindi voiceover script in Devanagari, conversational, spoken '
    "tense, no stage directions, no emoji, 150-260 seconds of speech at normal pace, "
    '"thumbnail_prompt": string - vivid prompt describing a custom thumbnail for this episode, '
    '"scenes": [{"visual_prompt": string, "narration_segment": string}] - 6 to 10 scenes covering '
    'the whole narration in order"}\n'
    "The narration must flow naturally when read aloud by a text-to-speech voice."
)


def _extract_json(text: str) -> dict:
    cleaned = text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(cleaned[start : end + 1])


def _validate(data: dict) -> dict:
    missing = [
        key
        for key in ("title", "description", "narration")
        if not str(data.get(key, "")).strip()
    ]
    if missing:
        raise ValueError(f"LLM script missing required fields: {', '.join(missing)}")
    data.setdefault("tags", [])
    data.setdefault("thumbnail_prompt", "")
    data.setdefault("scenes", [])
    return data


def _anthropic(prompt: str, settings: Settings) -> str:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.anthropic_model,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=180,
    )
    response.raise_for_status()
    blocks = response.json().get("content", [])
    return "".join(block.get("text", "") for block in blocks if block.get("type") == "text")


def _gemini(prompt: str, settings: Settings) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    response = requests.post(
        url,
        params={"key": settings.gemini_api_key},
        json={
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.8},
        },
        timeout=180,
    )
    response.raise_for_status()
    candidates = response.json().get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts)


PROVIDERS = {"anthropic": _anthropic, "gemini": _gemini}


def generate_script(topic: str, settings: Settings) -> dict:
    provider = PROVIDERS.get(settings.llm_provider)
    if provider is None:
        raise ValueError(f"Unknown LLM_PROVIDER '{settings.llm_provider}' (use anthropic|gemini)")
    prompt = f"Topic for this Chintu episode: {topic}"
    log.info("Generating script via %s for topic: %s", settings.llm_provider, topic)
    raw_text = provider(prompt, settings)
    script = _validate(_extract_json(raw_text))
    log.info("Script ready: %s", script["title"])
    return script
