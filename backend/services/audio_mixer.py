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

async def mix_audio(narration_path: Path, music_path: Path | None, background_audio_path: Path | None, output_path: Path,
                    narration_volume: float = 1.0, music_volume: float = 0.15, background_volume: float = 0.1) -> Path:
    """Mixes narration, background music, and ambient background audio."""
    if not narration_path.exists():
        raise FileNotFoundError(f"Narration file not found: {narration_path}")
        
    # Build filter complex for mixing
    # Inputs: 0:narration, 1:music (optional), 2:background_audio (optional)
    filter_complex = f"[0:a]volume={narration_volume}[n]"
    inputs = ["-i", str(narration_path)]
    mix_inputs = "[n]"
    num_inputs = 1
    
    if music_path and music_path.exists():
        inputs.extend(["-stream_loop", "-1", "-i", str(music_path)])
        filter_complex += f";[{num_inputs}:a]volume={music_volume}[m]"
        mix_inputs += "[m]"
        num_inputs += 1
        
    if background_audio_path and background_audio_path.exists():
        inputs.extend(["-stream_loop", "-1", "-i", str(background_audio_path)])
        filter_complex += f";[{num_inputs}:a]volume={background_volume}[b]"
        mix_inputs += "[b]"
        num_inputs += 1
        
    filter_complex += f";{mix_inputs}amix=inputs={num_inputs}:duration=first[out]"
    
    cmd = [
        "ffmpeg", "-y"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[out]", "-c:a", "pcm_s16le", str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path
