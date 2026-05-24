import subprocess
import logging
import json
import shutil
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

def get_duration(file_path: Path) -> float:
    """Gets duration of video/audio file using ffprobe."""
    if not file_path.exists():
        return 0.0
    
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting duration for {file_path}: {e}")
        return 0.0

def images_to_video(image_paths: List[Path], durations: List[float], output: Path, fps: int = 24):
    """Converts a list of images to a video sequence using an FFmpeg demuxer script."""
    # Create temporary concat text file
    concat_file = output.parent / "images_concat.txt"
    with open(concat_file, "w") as f:
        for img, dur in zip(image_paths, durations):
            f.write(f"file '{img.absolute()}'\n")
            f.write(f"duration {dur}\n")
        # Duplicate last image for FFmpeg requirements
        if image_paths:
            f.write(f"file '{image_paths[-1].absolute()}'\n")
            
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), "-preset", "ultrafast", str(output)
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    finally:
        if concat_file.exists():
            concat_file.unlink()

def add_audio_to_video(video: Path, audio: Path, output: Path):
    """Muxes audio and video streams together, ensuring full duration is preserved."""
    duration = get_duration(audio)
    if duration <= 0:
        duration = get_duration(video)
        
    cmd = [
        "ffmpeg", "-y", "-i", str(video), "-i", str(audio),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-t", str(duration), str(output)
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)

def concat_videos(videos: List[Path], output: Path):
    """Concatenates multiple video files using the FFmpeg concat demuxer."""
    concat_file = output.parent / "videos_concat.txt"
    with open(concat_file, "w") as f:
        for vid in videos:
            f.write(f"file '{vid.absolute()}'\n")
            
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(output)
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    finally:
        if concat_file.exists():
            concat_file.unlink()

def mix_audio(narration: Path, music: Path, output: Path, narration_volume: float = 1.0, music_volume: float = 0.15):
    """Mixes narration audio with background music, looping background music and adding fades."""
    duration = get_duration(narration)
    if duration <= 0:
        duration = 10.0 # Fallback
        
    # Standardize to WAV/PCM for intermediate mixing to avoid codec issues
    cmd = [
        "ffmpeg", "-y", "-i", str(narration), "-stream_loop", "-1", "-i", str(music),
        "-filter_complex",
        f"[0:a]volume={narration_volume * 1.5}[narr];"
        f"[1:a]volume={music_volume},afade=t=in:d=1.0,afade=t=out:st={max(0.0, duration-2.0)}:d=2.0[bg];"
        f"[narr][bg]amix=inputs=2:duration=first:dropout_transition=3[out]",
        "-map", "[out]", "-t", str(duration), "-c:a", "pcm_s16le", str(output)
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)

def burn_subtitles(video: Path, subtitle_file: Path, output: Path):
    """Burns subtitles (SRT or ASS) directly into the video stream."""
    sub_path = str(subtitle_file.absolute()).replace(":", "\\:")
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-vf", f"subtitles='{sub_path}'",
        "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast", "-c:a", "copy", str(output)
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)

def add_fade(video: Path, output: Path, duration: float, fade_in: float = 0.5, fade_out: float = 0.5):
    """Adds fade in and fade out visual effects to the video."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-vf", f"fade=t=in:st=0:d={fade_in},fade=t=out:st={max(0.0, duration-fade_out)}:d={fade_out}",
        "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast", "-c:a", "copy", str(output)
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)

def create_ken_burns_video(image: Path, output: Path, duration: float, fps: int = 24, 
                            effect: str = 'zoom_in', width: int = 1080, height: int = 1920) -> Path:
    """Uses FFmpeg's zoompan filter to create smooth camera movement from a static image."""
    # Cap frames at 3600 to avoid zoompan limitations (FFmpeg known bug/limit)
    total_frames = min(3600, int(duration * fps))
    actual_duration = total_frames / fps
    
    # Use 1.2x resolution for zoompan to keep it fast and stable on Intel Iris Xe / CPUs
    inter_w = int(width * 1.2)
    inter_h = int(height * 1.2)
    
    # Scale expressions for camera movement
    if effect == 'zoom_in':
        zoom_expr = f"min(1.2,zoom+0.1/{total_frames})"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif effect == 'zoom_out':
        zoom_expr = f"max(1.0,1.2-0.1*on/{total_frames})"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif effect == 'pan_left':
        zoom_expr = "1.1"
        x_expr = f"max(0,(iw-iw/zoom)*(1-on/{total_frames}))"
        y_expr = "ih/2-(ih/zoom/2)"
    elif effect == 'pan_right':
        zoom_expr = "1.1"
        x_expr = f"(iw-iw/zoom)*on/{total_frames}"
        y_expr = "ih/2-(ih/zoom/2)"
    elif effect == 'pan_up':
        zoom_expr = "1.1"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"max(0,(ih-ih/zoom)*(1-on/{total_frames}))"
    elif effect == 'pan_down':
        zoom_expr = "1.1"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"(ih-ih/zoom)*on/{total_frames}"
    else: # Default subtle zoom
        zoom_expr = f"min(1.1,zoom+0.05/{total_frames})"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"

    vf_chain = (
        f"scale={inter_w}x{inter_h},"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s={inter_w}x{inter_h}:fps={fps},"
        f"scale={width}x{height}"
    )
    
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-vf", vf_chain, "-t", str(actual_duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), "-preset", "ultrafast", str(output)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg Ken Burns failed: {e.stderr}")
        # Fallback to a simple static video clip
        cmd_fallback = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image),
            "-vf", f"scale={width}:{height}", "-t", str(actual_duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), "-preset", "ultrafast", str(output)
        ]
        subprocess.run(cmd_fallback, check=True, capture_output=True)
        
    return output
