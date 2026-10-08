import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATABASE_DIR = os.path.join(BASE_DIR, "database")

# YouTube API Credentials (Place your secrets here)
YOUTUBE_CLIENT_SECRETS_FILE = os.path.join(CONFIG_DIR, "client_secrets.json") if 'CONFIG_DIR' in locals() else os.path.join(BASE_DIR, "config", "client_secrets.json")
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Gemini API Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

# Video Settings
TARGET_RESOLUTION = (1080, 1920) # Shorts vertical format
BACKGROUND_MUSIC_VOLUME = 0.1 # 10% volume

# Asset Paths
BACKGROUND_MUSIC_PATH = os.path.join(ASSETS_DIR, "bg_music.mp3")
WATERMARK_CROP_PIXELS = 50 # Adjust based on the actual watermark size
