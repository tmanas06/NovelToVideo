from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SceneResponse(BaseModel):
    id: str
    project_id: str
    scene_number: int
    description: str
    image_prompt: Optional[str] = None
    image_path: Optional[str] = None
    narration_text: str
    audio_path: Optional[str] = None
    duration: float = 0.0
    animation_type: Optional[str] = None
    video_path: Optional[str] = None

    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    title: str
    story_text: str
    style: str = 'manga'

class ProjectResponse(BaseModel):
    id: str
    title: str
    story_text: str
    style: str = 'manga'
    status: str = 'draft'
    created_at: str
    updated_at: str
    scenes: List[SceneResponse] = []

    class Config:
        from_attributes = True

class JobCreate(BaseModel):
    project_id: str
    job_type: str = 'single'

class JobResponse(BaseModel):
    id: str
    project_id: str
    job_type: str = 'single'
    status: str = 'queued'
    progress: float = 0.0
    current_step: str = 'pending'
    log: str = ''
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True

class BatchCreate(BaseModel):
    stories: List[ProjectCreate]

class BatchResponse(BaseModel):
    batch_id: str
    jobs: List[JobResponse]

class SettingsUpdate(BaseModel):
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    comfyui_url: Optional[str] = None
    image_mode: Optional[str] = None
    image_api_url: Optional[str] = None
    image_api_key: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_speed: Optional[float] = None
    default_style: Optional[str] = None
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    video_fps: Optional[int] = None
    target_duration: Optional[int] = None
    scenes_per_story: Optional[int] = None
    output_dir: Optional[str] = None
    temp_dir: Optional[str] = None
    bg_music_volume: Optional[float] = None
    narration_volume: Optional[float] = None
