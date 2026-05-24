import logging
import subprocess
from pathlib import Path
from typing import List
from backend.utils.ffmpeg_utils import mix_audio as ffmpeg_mix_audio, get_duration

logger = logging.getLogger(__name__)

async def concat_audio_files(audio_files: List[Path], output_path: Path) -> Path:
    """Concatenates multiple audio files into a single continuous track using FFmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp concat file
    concat_file = output_path.parent / "audio_concat.txt"
    with open(concat_file, "w") as f:
        for audio in audio_files:
            f.write(f"file '{audio.absolute()}'\n")
            
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(output_path)
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error concatenating audio: {e.stderr}")
        # Fallback using amix / concat filter if direct copy fails
        filter_inputs = "".join([f"[{i}:a]" for i in range(len(audio_files))])
        cmd_fallback = ["ffmpeg", "-y"]
        for audio in audio_files:
            cmd_fallback.extend(["-i", str(audio)])
        cmd_fallback.extend([
            "-filter_complex", f"{filter_inputs}concat=n={len(audio_files)}:v=0:a=1[aout]",
            "-map", "[aout]", str(output_path)
        ])
        subprocess.run(cmd_fallback, check=True, capture_output=True)
    finally:
        if concat_file.exists():
            concat_file.unlink()
            
    return output_path

async def mix_audio(narration_path: Path, music_path: Path | None, output_path: Path,
                    narration_volume: float = 1.0, music_volume: float = 0.15,
                    fade_in: float = 1.0, fade_out: float = 2.0) -> Path:
    """Mixes narration speech with royalty-free music and loops/ducks appropriately."""
    if not narration_path.exists():
        raise FileNotFoundError(f"Narration file not found: {narration_path}")
        
    if not music_path or not music_path.exists():
        logger.warning("No music file provided or not found. Using pure narration audio.")
        # Just adjust volume on narration
        cmd = [
            "ffmpeg", "-y", "-i", str(narration_path),
            "-filter:a", f"volume={narration_volume}",
            "-c:a", "aac", str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
        
    logger.info(f"Mixing narration {narration_path.name} with music {music_path.name} (vol: {music_volume})")
    ffmpeg_mix_audio(
        narration=narration_path,
        music=music_path,
        output=output_path,
        narration_volume=narration_volume,
        music_volume=music_volume
    )
    return output_path
