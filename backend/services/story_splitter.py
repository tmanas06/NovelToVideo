import httpx
import json
import logging
import re
from typing import List, Dict, Any
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

async def split_story(story_text: str, num_scenes: int = 5, ollama_url: str = 'http://localhost:11434', model: str = 'qwen2.5:3b') -> List[Dict[str, Any]]:
    """Uses Ollama to split a story into key visual scenes with narration."""
    prompt = f"""
    Split the following story into exactly {num_scenes} visual scenes for a video.
    For each scene, provide:
    1. A brief visual description for an image generator.
    2. The narration text for that scene.

    STORY:
    {story_text}

    RESPONSE FORMAT (JSON ONLY):
    [
      {{"scene_number": 1, "description": "visual description", "narration_text": "narration text"}},
      ...
    ]
    """

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{ollama_url.rstrip('/')}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "[]")
                # Parse JSON from response
                scenes = json.loads(content)
                # Validation
                if isinstance(scenes, list) and len(scenes) > 0:
                    return scenes[:num_scenes]
            
            logger.error(f"Ollama returned status {response.status_code}")
            raise Exception("Invalid response from Ollama")

    except Exception as e:
        logger.error(f"Error calling Ollama story splitter: {e}")
        # Fallback: Divide the entire story into N roughly equal chunks
        logger.info(f"Using fallback chunking heuristic to split story into {num_scenes} scenes.")
        
        # Clean text
        text = story_text.strip()
        words = text.split()
        if not words:
            return [{"scene_number": 1, "description": "Empty story", "narration_text": "No content provided."}]
            
        chunk_size = len(words) // num_scenes
        if chunk_size == 0: chunk_size = 1
        
        scenes = []
        for i in range(num_scenes):
            start_idx = i * chunk_size
            # Last chunk takes the rest
            end_idx = (i + 1) * chunk_size if i < num_scenes - 1 else len(words)
            
            chunk_words = words[start_idx:end_idx]
            narration = " ".join(chunk_words)
            
            if not narration:
                continue
                
            scenes.append({
                "scene_number": i + 1,
                "description": f"Visual representation of: {narration[:100]}...",
                "narration_text": narration
            })
            
        return scenes
