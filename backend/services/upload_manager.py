import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class UploadManager:
    """Manages publishing of generated videos to platforms like YouTube and Instagram.
    Currently a stub waiting for production API credential setup in next phases.
    """
    
    def __init__(self):
        logger.info("UploadManager initialized in stub mode.")

    def upload_to_youtube(self, video_path: Path, title: str, description: str, tags: list[str] = None) -> str:
        """Uploads exported video to YouTube Shorts.
        
        To connect YouTube:
        1. Create a Google Cloud Project with the YouTube Data API v3 enabled.
        2. Set up OAuth2 credentials and download client_secrets.json.
        3. Authenticate to retrieve a refresh token.
        """
        message = (
            "YouTube Auto-Posting is not yet fully configured.\n\n"
            "To enable this integration:\n"
            "1. Run standard OAuth2 flow via scripts/auth_youtube.py\n"
            "2. Ensure client_secrets.json is present in the config/ directory.\n"
            "3. Update config settings with your YouTube Channel ID."
        )
        logger.warning("YouTube upload triggered, raising NotImplementedError stub.")
        raise NotImplementedError(message)

    def upload_to_instagram(self, video_path: Path, caption: str) -> str:
        """Uploads exported video to Instagram Reels.
        
        To connect Instagram:
        1. Register a Meta Developer App.
        2. Set up Instagram Graph API access.
        3. Obtain a long-lived page access token.
        """
        message = (
            "Instagram Reels Auto-Posting is not yet fully configured.\n\n"
            "To enable this integration:\n"
            "1. Enter your Instagram Page ID and Long-Lived User Access Token in Settings.\n"
            "2. Ensure your account is a Business or Creator account linked to a Facebook Page."
        )
        logger.warning("Instagram upload triggered, raising NotImplementedError stub.")
        raise NotImplementedError(message)

    def get_upload_status(self, upload_id: str) -> dict:
        """Queries status of an active asynchronous upload job."""
        raise NotImplementedError("Asynchronous upload queries will be supported once platform OAuth is configured.")
