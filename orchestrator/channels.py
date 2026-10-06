import logging

from googleapiclient.discovery import build

from .config import Settings
from .uploader import get_credentials

log = logging.getLogger(__name__)


def list_channels(settings: Settings) -> list[dict]:
    youtube = build("youtube", "v3", credentials=get_credentials(settings))
    response = (
        youtube.channels()
        .list(part="snippet,statistics,contentDetails", mine=True)
        .execute()
    )
    channels = []
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        statistics = item.get("statistics") or {}
        related = item.get("contentDetails", {}).get("relatedPlaylists", {})
        channels.append(
            {
                "id": item["id"],
                "title": snippet.get("title", ""),
                "custom_url": snippet.get("customUrl", ""),
                "published_at": snippet.get("publishedAt", ""),
                "country": snippet.get("country", ""),
                "subscribers": statistics.get("subscriberCount", "0"),
                "video_count": statistics.get("videoCount", "0"),
                "view_count": statistics.get("viewCount", "0"),
                "uploads_playlist": related.get("uploads", ""),
            }
        )
    log.info("Listed %d YouTube channel(s)", len(channels))
    return channels