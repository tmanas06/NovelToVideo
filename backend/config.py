import os
import json
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

PROJECT_ROOT = Path("/home/manas/Desktop/StoryToReel")

class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    comfyui_url: str = "http://localhost:8188"
    image_mode: str = "comfyui"  # comfyui, api, placeholder
    image_api_url: str = ""
    image_api_key: str = ""
    tts_voice: str = "en_US-lessac-medium"
    tts_speed: float = 1.0
    default_style: str = "manga"
    video_width: int = 1080
    video_height: int = 1920
    video_fps: int = 24
    target_duration: int = 30
    scenes_per_story: int = 5
    output_dir: str = "outputs"
    temp_dir: str = "temp"
    bg_music_volume: float = 0.15
    narration_volume: float = 1.0

    @property
    def output_path(self) -> Path:
        p = PROJECT_ROOT / self.output_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def temp_path(self) -> Path:
        p = PROJECT_ROOT / self.temp_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def database_path(self) -> Path:
        db_dir = PROJECT_ROOT / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "storytoreel.db"

_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        config_path = PROJECT_ROOT / "config" / "default_settings.json"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                _settings = Settings(**data)
            except Exception as e:
                print(f"Error loading default_settings.json: {e}. Using defaults.")
                _settings = Settings()
        else:
            _settings = Settings()
    return _settings
