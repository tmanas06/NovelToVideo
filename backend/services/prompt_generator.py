import httpx
import logging
from typing import List, Dict, Any
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

STYLE_PRESETS = {
    "manga": "manga style, detailed ink drawing, black and white with dramatic shading, high contrast, Japanese manga art, graphic novel visual",
    "anime": "anime style, vibrant colors, detailed character design, Studio Ghibli quality, beautiful fantasy lighting, masterwork anime key visual",
    "realistic": "photorealistic, cinematic photography, 8k resolution, intricate details, highly professional lighting, dramatic atmosphere, photo",
    "fantasy": "fantasy art style, magical atmosphere, ethereal glow, detailed mystical environment, epic landscape composition, fantasy concept art",
    "dark": "dark gothic art style, moody atmosphere, deep shadows, dramatic contrast, noir aesthetic, dark fantasy theme",
    "cinematic": "cinematic style, dramatic movie still, professional color grading, anamorphic lens flare, award-winning cinematography, highly detailed"
}

async def generate_prompts(scenes: List[Dict[str, Any]], style: str = 'manga', ollama_url: str = 'http://localhost:11434', model: str = 'qwen2.5:3b') -> List[Dict[str, Any]]:
    """Converts a list of scene visual descriptions into highly detailed image generation prompts using Ollama."""
    style_preset = STYLE_PRESETS.get(style.lower(), STYLE_PRESETS["manga"])
    enhanced_scenes = []

    for scene in scenes:
        scene_num = scene.get("scene_number", 1)
        desc = scene.get("description", "")
        
        system_prompt = (
            f"You are an expert prompt engineer for generative AI models like Stable Diffusion.\n"
            f"Your job is to expand the given visual scene description into a highly detailed, descriptive, single-paragraph prompt optimized for generating a high-quality vertical portrait image (9:16 aspect ratio).\n"
            f"Focus on styling, subject, action, composition, camera shot type, lighting, textures, and color. Include the following style direction: {style_preset}.\n"
            f"Output ONLY the prompt text, with no preamble, formatting, quotes, or conversational notes."
        )

        url = f"{ollama_url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": f"Scene description to expand:\n{desc}",
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.6
            }
        }

        image_prompt = ""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    image_prompt = result.get("response", "").strip()
        except Exception as e:
            logger.error(f"Error calling Ollama prompt generator for scene {scene_num}: {e}")

        # Fallback if Ollama fails or is unreachable
        if not image_prompt:
            image_prompt = f"{desc}, {style_preset}"

        # Clean prompt (remove markdown bold/quotes)
        image_prompt = image_prompt.replace('"', '').replace('**', '').replace('`', '').strip()
        
        # Append quality tags
        positive_prompt = f"{image_prompt}, highly detailed, masterpiece, stunning visual, 4k, vertical orientation, portrait ratio"
        negative_prompt = "blurry, low quality, distorted, watermark, text, signature, low-res, extra limbs, bad anatomy, worst quality, landscape ratio, horizontal orientation, borders"

        enhanced_scene = scene.copy()
        enhanced_scene["image_prompt"] = positive_prompt
        enhanced_scene["negative_prompt"] = negative_prompt
        enhanced_scenes.append(enhanced_scene)

    return enhanced_scenes
