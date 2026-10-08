import logging
import requests
import time
from pathlib import Path
from google.cloud import storage
from .config import Settings

BUCKET_NAME = "chintu-videos-project-f5ca84bb-cf62-4be3-b59"

def _upload_to_gcs(video_path: Path) -> str:
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob_name = f"videos/{video_path.name}"
    blob = bucket.blob(blob_name)
    log.info("Uploading %s to GCS gs://%s/%s", video_path.name, BUCKET_NAME, blob_name)
    blob.upload_from_filename(str(video_path))
    return f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

log = logging.getLogger(__name__)


def publish_to_instagram(video_path: Path, script: dict, settings: Settings) -> dict:
    if not settings.ig_access_token or not settings.ig_user_id:
        log.warning("IG_ACCESS_TOKEN or IG_USER_ID missing. Skipping Instagram.")
        return {"status": "skipped", "reason": "missing credentials"}
    
    log.info("Starting Instagram upload for %s", video_path.name)
    caption = f"{script.get('title', 'Chintu\\'s Adventure')}\n\n{script.get('description', '')}\n\n#ChintusTechAdventures #KidsCoding #LearnWithChintu"

    video_url = _upload_to_gcs(video_path)
    
    log.info("Uploaded to GCS: %s. Calling IG Graph API", video_url)
    
    url = f"https://graph.facebook.com/v19.0/{settings.ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": settings.ig_access_token
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    creation_id = resp.json().get("id")
    
    log.info("Container %s created. Waiting for IG to process video...", creation_id)
    time.sleep(30)
    
    publish_url = f"https://graph.facebook.com/v19.0/{settings.ig_user_id}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": settings.ig_access_token
    }
    publish_resp = requests.post(publish_url, json=publish_payload)
    publish_resp.raise_for_status()
    
    return {"status": "success", "platform": "instagram"}


def publish_to_pinterest(video_path: Path, script: dict, settings: Settings) -> dict:
    if not settings.pinterest_access_token or not settings.pinterest_board_id:
        log.warning("PINTEREST_ACCESS_TOKEN or PINTEREST_BOARD_ID missing. Skipping Pinterest.")
        return {"status": "skipped", "reason": "missing credentials"}

    log.info("Starting Pinterest upload for %s", video_path.name)
    title = script.get("title", "Chintu's Adventure")
    description = f"{script.get('description', '')} #ChintusTechAdventures"
    
    # Register Media Upload
    log.info("Registering media upload with Pinterest API...")
    url = "https://api.pinterest.com/v5/media"
    payload = {"media_type": "video"}
    headers = {
        "Authorization": f"Bearer {settings.pinterest_access_token}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    
    media_data = resp.json()
    media_id = media_data["media_id"]
    upload_url = media_data["upload_url"]
    upload_parameters = media_data["upload_parameters"]
    
    # Upload to AWS S3 (Pinterest provided URL)
    log.info("Uploading video bytes to Pinterest S3...")
    with open(video_path, "rb") as f:
        files = {"file": f}
        s3_resp = requests.post(upload_url, data=upload_parameters, files=files)
        s3_resp.raise_for_status()
        
    log.info("S3 upload complete. Waiting for processing...")
    time.sleep(15)
    
    # Create Pin
    log.info("Creating Pinterest Pin...")
    pin_url = "https://api.pinterest.com/v5/pins"
    pin_payload = {
        "board_id": settings.pinterest_board_id,
        "media_source": {"source_type": "video_id", "media_id": media_id},
        "title": title[:100],
        "description": description[:500]
    }
    pin_resp = requests.post(pin_url, headers=headers, json=pin_payload)
    pin_resp.raise_for_status()
    
    return {"status": "success", "platform": "pinterest"}
