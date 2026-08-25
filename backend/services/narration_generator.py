import subprocess
import logging
import shutil
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from backend.config import get_settings, PROJECT_ROOT
from backend.utils.file_utils import get_project_audio_dir
from backend.utils.ffmpeg_utils import get_duration

logger = logging.getLogger(__name__)
settings = get_settings()

async def generate_narration(text: str, output_path: Path, voice: str = 'en_US-lessac-medium', speed: float = 1.0) -> Dict[str, Any]:
    """Generates narration audio file from text using Piper TTS with robust fallback."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if Piper is installed
    piper_bin = shutil.which("piper")
    # Path to voice model
    voice_dir = PROJECT_ROOT / "assets" / "voices"
    voice_dir.mkdir(parents=True, exist_ok=True)
    voice_model_path = voice_dir / f"{voice}.onnx"
    
    # Check for local virtualenv piper binary
    if not piper_bin:
        local_piper = PROJECT_ROOT / "venv" / "bin" / "piper"
        if local_piper.exists():
            piper_bin = str(local_piper)
            
    if piper_bin and voice_model_path.exists():
        logger.info(f"Using Piper TTS to generate narration: '{text[:30]}...'")
        cmd = [
            piper_bin,
            "--model", str(voice_model_path),
            "--output_file", str(output_path)
        ]
        
        # Piper also supports custom speed
        if speed != 1.0:
            cmd.extend(["--length_scale", str(1.0 / speed)])
            
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=text.encode('utf-8'))
            if process.returncode == 0 and output_path.exists():
                duration = get_duration(output_path)
                return {"audio_path": str(output_path), "duration": duration}
            else:
                logger.error(f"Piper TTS command failed with code {process.returncode}: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Error running Piper TTS: {e}")

    # Fallback to espeak
    espeak_bin = shutil.which("espeak") or shutil.which("espeak-ng")
    if espeak_bin:
        logger.info(f"Piper TTS not available. Falling back to espeak...")
        temp_wav = output_path.parent / f"temp_{output_path.name}"
        # espeak generates wav
        cmd = [espeak_bin, "-w", str(temp_wav), text]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            # Use FFmpeg to convert it and adjust speed if needed
            speed_filter = f"atempo={speed}" if speed != 1.0 else "copy"
            cmd_ffmpeg = [
                "ffmpeg", "-y", "-i", str(temp_wav),
                "-filter:a", speed_filter, str(output_path)
            ]
            subprocess.run(cmd_ffmpeg, check=True, capture_output=True)
            if temp_wav.exists():
                temp_wav.unlink()
            duration = get_duration(output_path)
            return {"audio_path": str(output_path), "duration": duration}
        except Exception as e:
            logger.error(f"espeak fallback failed: {e}")
            if temp_wav.exists():
                temp_wav.unlink()

    # Absolute fallback: Generate silence of matching duration based on average speaking speed
    logger.warning("No TTS engine available! Generating silent audio fallback matching estimated word duration.")
    words = len(text.split())
    # 2.5 words per second is average speech rate
    estimated_duration = max(1.5, words / 2.3)
    cmd_silent = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=22050:cl=mono",
        "-t", str(estimated_duration), "-c:a", "pcm_s16le", str(output_path)
    ]
    try:
        subprocess.run(cmd_silent, check=True, capture_output=True)
        duration = get_duration(output_path)
        return {"audio_path": str(output_path), "duration": duration}
    except Exception as e:
        logger.error(f"Silent audio fallback failed: {e}")
        return {"audio_path": "", "duration": 0.0}

async def generate_all_narrations(scenes: List[Dict[str, Any]], project_id: str, voice: str = 'en_US-lessac-medium', speed: float = 1.0) -> List[Dict[str, Any]]:
    """Generates narration audio for all scenes in a project."""
    audio_dir = get_project_audio_dir(project_id)
    updated_scenes = []
    
    for scene in scenes:
        scene_num = scene.get("scene_number", 1)
        text = scene.get("narration_text", "And then it happened.")
        output_path = audio_dir / f"narration_{scene_num:02d}.wav"
        
        result = await generate_narration(text, output_path, voice, speed)
        
        updated_scene = scene.copy()
        updated_scene["audio_path"] = result.get("audio_path", "")
        updated_scene["duration"] = result.get("duration", 0.0)
        updated_scenes.append(updated_scene)
        
    return updated_scenes
