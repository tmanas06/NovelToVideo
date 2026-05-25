import asyncio
import logging
import random
from pathlib import Path
from typing import Callable
from backend.config import get_settings
from backend.database.db import get_project, create_scene, get_scenes, update_scene
from backend.services.story_splitter import split_story
from backend.services.prompt_generator import generate_prompts
from backend.services.image_generator import generate_images_for_project
from backend.services.narration_generator import generate_all_narrations
from backend.services.animation_engine import create_all_animated_clips
from backend.services.subtitle_generator import generate_ass
from backend.services.audio_mixer import concat_audio_files, mix_audio
from backend.services.video_builder import build_video
from backend.utils.ffmpeg_utils import concat_videos
from backend.utils.file_utils import get_project_audio_dir, get_project_video_dir, get_output_path

logger = logging.getLogger(__name__)
settings = get_settings()

async def run_pipeline(project_id: str, job_id: str, progress_callback: Callable[[str, float, str], None], log_callback: Callable[[str, str], None] = None):
    """Orchestrates the entire StoryToReel video generation pipeline end-to-end."""

    def log(msg, level="info"):
        if log_callback:
            log_callback(level, msg)
        logger.info(msg)

    try:
        log(f"--- Pipeline started for project {project_id} ---")

        # 1. Fetch project
        progress_callback("loading_project", 0.05, "Fetching project data and preparing background assets...")
        log("Fetching project data from DB and selecting background assets...")
        project = await get_project(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found in database.")

        # Asset selection
        visuals_dir = Path("/home/manas/Desktop/StoryToReel/assets/backgrounds/visuals")
        audio_dir = Path("/home/manas/Desktop/StoryToReel/assets/backgrounds/audio")
        
        visual_files = list(visuals_dir.glob("*.mp4"))
        audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))
        
        # Select multiple to cover duration
        selected_visuals = random.sample(visual_files, min(len(visual_files), 3)) if visual_files else []
        selected_audios = random.sample(audio_files, min(len(audio_files), 3)) if audio_files else []
        
        # Concatenate assets
        audio_dir_path = get_project_audio_dir(project_id)
        video_dir_path = get_project_video_dir(project_id)
        
        combined_audio = audio_dir_path / "combined_bg_audio.wav"
        combined_video = video_dir_path / "combined_bg_video.mp4"
        
        if selected_audios:
            await concat_audio_files(selected_audios, combined_audio)
        else:
            combined_audio = None
            
        if selected_visuals:
            concat_videos(selected_visuals, combined_video)
        else:
            combined_video = None
        
        log(f"Concatenated {len(selected_visuals)} visuals and {len(selected_audios)} audios for background.")

        title = project["title"]
        story_text = project["story_text"]
        style = project["style"]

        # 2. Scene Extraction
        progress_callback("scene_extraction", 0.10, f"Splitting story into scenes using LLM model {settings.ollama_model}...")
        log(f"Calling Ollama for scene extraction (model: {settings.ollama_model})...")
        scenes = await split_story(
            story_text=story_text,
            num_scenes=settings.scenes_per_story,
            ollama_url=settings.ollama_url,
            model=settings.ollama_model
        )

        # Write initial scenes to database
        if not scenes:
            raise ValueError("No scenes could be extracted or generated.")
            
        progress_callback("saving_scenes", 0.15, f"Extracted {len(scenes)} scenes. Saving storyboard entries...")
        log(f"Extracted {len(scenes)} scenes. Creating DB records.")
        db_scenes = []
        for s in scenes:
            db_s = await create_scene(
                project_id=project_id,
                scene_number=s["scene_number"],
                description=s["description"],
                narration_text=s["narration_text"]
            )
            db_scenes.append(db_s)

        # 3. Prompt Generation
        progress_callback("prompt_generation", 0.20, f"Expanding visual scenes into detailed {style} prompts via Ollama...")
        log(f"Generating visual prompts for style: {style}")
        enhanced_scenes = await generate_prompts(
            scenes=db_scenes,
            style=style,
            ollama_url=settings.ollama_url,
            model=settings.ollama_model
        )

        # Update scenes with prompts in database
        for s in enhanced_scenes:
            await update_scene(s["id"], image_prompt=s["image_prompt"], negative_prompt=s["negative_prompt"])

        # 4. Image Generation
        progress_callback("image_generation", 0.25, f"Generating {len(enhanced_scenes)} story scenes using {settings.image_mode} mode...")
        log(f"Starting image generation in {settings.image_mode} mode")

        # Call sequential generator
        scenes_with_images = await generate_images_for_project(
            scenes=enhanced_scenes,
            project_id=project_id,
            image_mode=settings.image_mode,
            video_width=settings.video_width,
            video_height=settings.video_height,
            comfyui_url=settings.comfyui_url,
            image_api_url=settings.image_api_url,
            image_api_key=settings.image_api_key,
            log_callback=log_callback
        )

        # Update scenes with image paths in database
        for i, s in enumerate(scenes_with_images):
            await update_scene(s["id"], image_path=s["image_path"])
            progress_callback("image_generation", 0.25 + 0.30 * ((i+1) / len(scenes_with_images)), f"Generated image for scene {s['scene_number']}/{len(scenes_with_images)}")

        # 5. Narration Generation
        progress_callback("narration_generation", 0.55, f"Synthesizing speech voiceovers with Piper TTS...")
        log(f"Synthesizing speech with Piper (voice: {settings.tts_voice})")
        scenes_with_audio = await generate_all_narrations(
            scenes=scenes_with_images,
            project_id=project_id,
            voice=settings.tts_voice,
            speed=settings.tts_speed
        )

        # Update scenes with audio paths and duration in database
        for s in scenes_with_audio:
            await update_scene(s["id"], audio_path=s["audio_path"], duration=s["duration"])

        # 6. Camera Movement Animation
        progress_callback("animation_generation", 0.70, "Animating static images using camera panning/zooming effects...")
        log("Generating FFmpeg zoompan animations...")
        scenes_with_video = await create_all_animated_clips(
            scenes=scenes_with_audio,
            project_id=project_id,
            fps=settings.video_fps,
            width=settings.video_width,
            height=settings.video_height,
            log_callback=log_callback
        )

        # Update scenes with video clip paths in database
        for s in scenes_with_video:
            await update_scene(s["id"], animation_type=s["animation_type"], video_path=s["video_path"])

        # 7. Subtitle Generation
        progress_callback("subtitle_generation", 0.80, "Auto-generating and timing reels-style subtitles...")
        log("Creating ASS subtitle file...")
        sub_dir = get_project_video_dir(project_id)
        subtitle_path = sub_dir / "subtitles.ass"

        # Download font if not present / select available system font
        font_path = Path("/home/manas/Desktop/StoryToReel/assets/fonts/Inter-Bold.ttf")
        font_name = "Inter" if font_path.exists() else "DejaVu Sans"

        generate_ass(
            scenes=scenes_with_video,
            output_path=subtitle_path,
            font_name=font_name,
            font_size=18,
            bold=True
        )

        # 8. Audio Mixing
        progress_callback("audio_mixing", 0.82, "Mixing narration clips and applying volume-ducked background music...")
        log("Mixing audio layers...")
        audio_dir = get_project_audio_dir(project_id)
        concated_audio = audio_dir / "concat_narration.wav"
        mixed_audio = audio_dir / "mixed_final.wav"

        # Concat all individual narration wavs
        narration_files = [Path(s["audio_path"]) for s in scenes_with_video if s.get("audio_path")]
        await concat_audio_files(narration_files, concated_audio)

        # Check for background music in assets/music/
        music_dir = Path("/home/manas/Desktop/StoryToReel/assets/music")
        music_tracks = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
        selected_music = music_tracks[0] if music_tracks else None

        await mix_audio(
            narration_path=concated_audio,
            music_path=selected_music,
            background_audio_path=combined_audio,
            output_path=mixed_audio,
            narration_volume=settings.narration_volume,
            music_volume=settings.bg_music_volume
        )

        # 9. Final Video Assembly
        progress_callback("video_assembly", 0.88, "Stitching scene video clips together, burning subtitles and rendering final MP4...")
        log("Final assembly and subtitle burn-in...")
        final_output = get_output_path(project_id, title)

        await build_video(
            project_id=project_id,
            scenes=scenes_with_video,
            subtitle_path=subtitle_path,
            mixed_audio_path=mixed_audio,
            output_path=final_output,
            width=settings.video_width,
            height=settings.video_height,
            fps=settings.video_fps,
            log_callback=log_callback
        )

        progress_callback("finished", 1.00, f"Video generated successfully! Saved to: {final_output.name}")
        log(f"Pipeline finished successfully for {project_id}")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        log(f"FATAL ERROR in pipeline: {str(e)}", level="error")
        log(error_trace, level="error")
        progress_callback("failed", 1.0, f"Pipeline crashed: {str(e)}")
        raise e
