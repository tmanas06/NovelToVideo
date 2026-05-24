import re
from pathlib import Path
from typing import List, Dict, Any

def format_srt_time(seconds: float) -> str:
    """Formats float seconds into SRT time format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_ass_time(seconds: float) -> str:
    """Formats float seconds into ASS time format: H:MM:SS.CC"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis == 100:
        secs += 1
        centis = 0
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{centis:02d}"

def chunk_text(text: str, max_words: int = 6) -> List[str]:
    """Splits a single paragraph into smaller readable subtitle chunks."""
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= max_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def generate_srt(scenes: List[Dict[str, Any]], output_path: Path) -> Path:
    """Generates standard SRT subtitles from scenes narration."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cumulative_time = 0.0
    srt_index = 1
    
    with open(output_path, "w", encoding="utf-8") as f:
        for scene in scenes:
            text = scene.get("narration_text", "")
            duration = scene.get("duration", 5.0)
            if not text:
                cumulative_time += duration
                continue
                
            chunks = chunk_text(text, max_words=6)
            if not chunks:
                cumulative_time += duration
                continue
                
            time_per_chunk = duration / len(chunks)
            
            for chunk in chunks:
                start_time = cumulative_time
                end_time = cumulative_time + time_per_chunk
                
                f.write(f"{srt_index}\n")
                f.write(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n")
                f.write(f"{chunk}\n\n")
                
                srt_index += 1
                cumulative_time = end_time
                
    return output_path

def generate_ass(scenes: List[Dict[str, Any]], output_path: Path, 
                  font_name: str = 'Inter', font_size: int = 16,
                  primary_color: str = '&H00FFFFFF', outline_color: str = '&H00000000',
                  bold: bool = True, alignment: int = 2) -> Path:
    """Generates styled ASS subtitles (karaoke-style visual highlighting or bold center style)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # ASS style template
    font_weight = "-1" if bold else "0"
    
    ass_header = (
        "[Script Info]\n"
        "Title: StoryToReel Subtitles\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font_name},{font_size},{primary_color},&H0000FFFF,{outline_color},&H80000000,{font_weight},0,0,0,100,100,0,0,1,3,1.5,{alignment},30,30,120,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    
    cumulative_time = 0.0
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        
        for scene in scenes:
            text = scene.get("narration_text", "")
            duration = scene.get("duration", 5.0)
            if not text:
                cumulative_time += duration
                continue
                
            chunks = chunk_text(text, max_words=4) # Smaller chunks for neat vertical reels
            if not chunks:
                cumulative_time += duration
                continue
                
            time_per_chunk = duration / len(chunks)
            
            for chunk in chunks:
                start_time = cumulative_time
                end_time = cumulative_time + time_per_chunk
                
                start_str = format_ass_time(start_time)
                end_str = format_ass_time(end_time)
                
                # Clean text for ASS compatibility
                clean_chunk = chunk.replace('"', '\\"').strip()
                # Uppercase for Reels dynamic impact style
                clean_chunk = clean_chunk.upper()
                
                f.write(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{clean_chunk}\n")
                
                cumulative_time = end_time
                
    return output_path

def generate_word_by_word_ass(scenes: List[Dict[str, Any]], output_path: Path, 
                              font_name: str = 'Inter', font_size: int = 18) -> Path:
    """Creates a TikTok/Reels style word-by-word karaoke subtitle."""
    # For simplicity, we split words and color-highlight the currently active word
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    ass_header = (
        "[Script Info]\n"
        "Title: StoryToReel Karaoke Subtitles\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1.5,2,30,30,120,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    
    cumulative_time = 0.0
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        
        for scene in scenes:
            text = scene.get("narration_text", "")
            duration = scene.get("duration", 5.0)
            if not text:
                cumulative_time += duration
                continue
                
            words = text.split()
            if not words:
                cumulative_time += duration
                continue
                
            # Distribute time evenly among all words in the scene
            time_per_word = duration / len(words)
            
            # Group into short phrases of 3 words max, showing a rolling active highlighted word
            phrase_size = 3
            for idx in range(0, len(words), phrase_size):
                phrase_words = words[idx:idx + phrase_size]
                phrase_duration = len(phrase_words) * time_per_word
                phrase_start = cumulative_time
                phrase_end = cumulative_time + phrase_duration
                
                # For this phrase, create an ASS event with karaoke tags: \k or custom styling
                # e.g., Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,{\kf30}WORD1 {\kf30}WORD2 {\kf30}WORD3
                karaoke_text = ""
                for word_offset, w in enumerate(phrase_words):
                    centisec = int(time_per_word * 100)
                    # Use \kf tag for fill karaoke effect
                    karaoke_text += f"{{\\kf{centisec}}}{w.upper()} "
                    
                start_str = format_ass_time(phrase_start)
                end_str = format_ass_time(phrase_end)
                
                f.write(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{karaoke_text.strip()}\n")
                cumulative_time = phrase_end
                
    return output_path
