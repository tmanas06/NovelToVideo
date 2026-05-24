import re
import shutil
from pathlib import Path
from backend.config import get_settings

settings = get_settings()

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_project_dir(project_id: str) -> Path:
    p = settings.temp_path / project_id
    ensure_dir(p)
    return p

def get_project_images_dir(project_id: str) -> Path:
    p = get_project_dir(project_id) / "images"
    ensure_dir(p)
    return p

def get_project_audio_dir(project_id: str) -> Path:
    p = get_project_dir(project_id) / "audio"
    ensure_dir(p)
    return p

def get_project_video_dir(project_id: str) -> Path:
    p = get_project_dir(project_id) / "video"
    ensure_dir(p)
    return p

def cleanup_project_temp(project_id: str):
    p = get_project_dir(project_id)
    if p.exists() and p.is_dir():
        shutil.rmtree(p)

def sanitize_filename(name: str) -> str:
    # Keep alphanumeric, spaces, and hyphens, replace others with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9\s\-]', '_', name)
    # Replace spaces with hyphens, lowercase
    sanitized = re.sub(r'\s+', '-', sanitized).strip().lower()
    return sanitized if sanitized else "project"

def get_output_path(project_id: str, title: str) -> Path:
    sanitized_title = sanitize_filename(title)
    short_id = project_id[:8]
    filename = f"{sanitized_title}_{short_id}.mp4"
    return settings.output_path / filename
