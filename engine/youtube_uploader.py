import os
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

class YouTubeUploader:
    def __init__(self, config):
        self.config = config
        self.youtube = self.get_authenticated_service()

    def get_authenticated_service(self):
        print("Authenticating with YouTube API...")
        # Path to client_secrets.json (Needs to be downloaded from Google Cloud Console)
        client_secrets_file = self.config.YOUTUBE_CLIENT_SECRETS_FILE
        
        if not os.path.exists(client_secrets_file):
            print(f"Error: Client secrets file not found at {client_secrets_file}")
            print("Please create a project in Google Cloud Console, enable YouTube Data API v3, create OAuth 2.0 Client IDs, download the JSON and place it in the config folder.")
            return None

        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, self.config.YOUTUBE_SCOPES)
        
        # This will open a browser window for authentication
        credentials = flow.run_local_server(port=0)
        
        return build(self.config.YOUTUBE_API_SERVICE_NAME, self.config.YOUTUBE_API_VERSION, credentials=credentials)

    def upload_video(self, file_path, title, description, tags, category_id="27"):
        """
        Uploads a video to YouTube. category_id 27 is Education.
        """
        if not self.youtube:
            print("Cannot upload: YouTube service not authenticated.")
            return False

        print(f"Uploading {file_path} to YouTube...")
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': 'private' # Set to 'private' for testing, 'public' for production
            }
        }

        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        
        try:
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            response = request.execute()
            print(f"Video uploaded successfully! Video ID: {response['id']}")
            return response['id']
            
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred during upload: {e}")
            return False
