import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .config import Settings

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def get_credentials(settings: Settings) -> Credentials:
    credentials = None
    token_file = settings.youtube_token_file
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    elif not credentials or not credentials.valid:
        if not settings.youtube_client_secret_file.exists():
            raise FileNotFoundError(
                f"YouTube client secret not found: {settings.youtube_client_secret_file}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(settings.youtube_client_secret_file), SCOPES
        )
        credentials = flow.run_local_server(port=0)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def upload_video(
    video_path: Path,
    script: dict,
    thumbnail_path: Path | None,
    settings: Settings,
) -> dict:
    if not video_path.is_file():
        raise FileNotFoundError(video_path)
    credentials = get_credentials(settings)
    youtube = build("youtube", "v3", credentials=credentials)

    tags = list(dict.fromkeys([*settings.youtube_default_tags, *script.get("tags", [])]))[:30]
    body = {
        "snippet": {
            "title": script["title"][:100],
            "description": script["description"],
            "tags": tags,
            "categoryId": settings.youtube_category_id,
        },
        "status": {
            "privacyStatus": settings.youtube_privacy_status,
            "selfDeclaredMadeForKids": True,
        },
    }

    log.info("Uploading to YouTube: %s", body["snippet"]["title"])
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log.info("Upload progress: %d%%", int(status.progress() * 100))

    video_id = response["id"]
    if thumbnail_path and thumbnail_path.is_file():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/png"),
        ).execute()
        log.info("Custom thumbnail set")

    url = f"https://youtu.be/{video_id}"
    log.info("Published: %s", url)
    return {"video_id": video_id, "url": url, "title": body["snippet"]["title"]}
