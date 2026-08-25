import random
import logging
from pathlib import Path
from typing import List, Dict, Any
from backend.config import get_settings, PROJECT_ROOT
from backend.utils.file_utils import get_project_video_dir
from backend.utils.ffmpeg_utils import create_ken_burns_video

logger = logging.getLogger(__name__)
settings = get_settings()

ANIMATION_TYPES = ['zoom_in', 'zoom_out', 'pan_left', 'pan_right', 'pan_up', 'pan_down']

def get_random_animation() -> str:
    return random.choice(ANIMATION_TYPES)

async def create_animated_clip(image_path: Path, output_path: Path, duration: float, 
                               fps: int = 24, effect: str = 'zoom_in',
                               width: int = 1080, height: int = 1920) -> Path:
    """Animates a single static image over a duration using the Ken Burns effect."""
    if not image_path.exists():
        raise FileNotFoundError(f"Source image not found: {image_path}")
        
    if not effect or effect not in ANIMATION_TYPES:
        effect = get_random_animation()
        
    logger.info(f"Creating animated clip for {image_path.name} with effect '{effect}' for {duration}s")
    return create_ken_burns_video(
        image=image_path,
        output=output_path,
        duration=duration,
        fps=fps,
        effect=effect,
        width=width,
        height=height
    )

async def create_all_animated_clips(scenes: List[Dict[str, Any]], project_id: str, 
                                    fps: int = 24, width: int = 1080, height: int = 1920,
                                    log_callback=None) -> List[Dict[str, Any]]:
    """Creates individual camera-animated video clips for every scene in the project."""
    video_dir = get_project_video_dir(project_id)
    updated_scenes = []
    
    for scene in scenes:
        scene_num = scene.get("scene_number", 1)
        image_path_str = scene.get("image_path")
        duration = scene.get("duration", 5.0) # Fallback to 5 seconds
        if duration <= 0:
            duration = 5.0
            
        effect = scene.get("animation_type")
        if not effect:
            effect = get_random_animation()
            
        if not image_path_str:
            logger.error(f"Cannot animate scene {scene_num}: Image path is missing!")
            # Save a placeholder image first
            img_dir = PROJECT_ROOT / "temp" / project_id / "images" / f"scene_{scene_num:02d}.png"
            from backend.services.image_generator import generate_placeholder_image
            generate_placeholder_image(scene.get("description", "A dramatic moment"), img_dir, width, height)
            image_path_str = str(img_dir)
            
        image_path = Path(image_path_str)
        output_path = video_dir / f"scene_clip_{scene_num:02d}.mp4"
        
        if log_callback:
            log_callback("info", f"Animating scene {scene_num} with {effect} for {duration}s...")
            
        final_clip = await create_animated_clip(
            image_path=image_path,
            output_path=output_path,
            duration=duration,
            fps=fps,
            effect=effect,
            width=width,
            height=height
        )
        
        if log_callback:
            log_callback("success", f"Scene {scene_num} animation completed.")
            
        updated_scene = scene.copy()
        updated_scene["animation_type"] = effect
        updated_scene["video_path"] = str(final_clip)
        updated_scenes.append(updated_scene)
        
    return updated_scenes
