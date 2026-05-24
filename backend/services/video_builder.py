import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any
from backend.utils.ffmpeg_utils import concat_videos, add_audio_to_video, burn_subtitles, add_fade, get_duration
from backend.utils.file_utils import get_project_video_dir, get_output_path

logger = logging.getLogger(__name__)

async def build_video(project_id: str, scenes: List[Dict[str, Any]], 
                       subtitle_path: Path | None = None,
                       mixed_audio_path: Path | None = None,
                       output_path: Path = None,
                       width: int = 1080, height: int = 1920,
                       fps: int = 24,
                       log_callback=None) -> Path:
    """Assembles animated scene clips, mixed audio, and subtitles into a final MP4 video."""
    video_dir = get_project_video_dir(project_id)
    
    # 1. Get scene video clips
    clip_paths = []
    for scene in scenes:
        v_path = scene.get("video_path")
        if v_path and Path(v_path).exists():
            clip_paths.append(Path(v_path))
        else:
            raise FileNotFoundError(f"Missing animated video clip for scene {scene.get('scene_number')}")
            
    if not clip_paths:
        raise ValueError("No video clips available to assemble!")
        
    if log_callback:
        log_callback("info", f"Concatenating {len(clip_paths)} clips for project {project_id}")
    concated_video_path = video_dir / "concated_raw.mp4"
    concat_videos(clip_paths, concated_video_path)
    
    # 2. Add mixed audio
    video_with_audio_path = video_dir / "video_with_audio.mp4"
    if mixed_audio_path and mixed_audio_path.exists():
        if log_callback:
            log_callback("info", f"Adding mixed audio stream {mixed_audio_path.name} to video")
        add_audio_to_video(concated_video_path, mixed_audio_path, video_with_audio_path)
    else:
        logger.warning("No mixed audio stream provided. Video will have no sound.")
        shutil.copy(concated_video_path, video_with_audio_path)
        
    # 3. Burn in subtitles if provided
    final_video_before_fade = video_dir / "video_with_subs.mp4"
    if subtitle_path and subtitle_path.exists():
        if log_callback:
            log_callback("info", f"Burning subtitles from {subtitle_path.name} into video")
        try:
            burn_subtitles(video_with_audio_path, subtitle_path, final_video_before_fade)
        except Exception as e:
            logger.error(f"Subtitle burn-in failed: {e}. Outputting video without subtitles.")
            shutil.copy(video_with_audio_path, final_video_before_fade)
    else:
        shutil.copy(video_with_audio_path, final_video_before_fade)
        
    # 4. Add video fade in/out
    total_duration = get_duration(final_video_before_fade)
    if log_callback:
        log_callback("info", f"Applying visual fade-in and fade-out (total duration: {total_duration}s)")
    add_fade(
        video=final_video_before_fade,
        output=output_path,
        duration=total_duration,
        fade_in=0.5,
        fade_out=0.5
    )
    
    if log_callback:
        log_callback("success", f"Successfully assembled final video exported to: {output_path.name}")
    return output_path
