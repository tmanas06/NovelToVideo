import httpx
import logging
from typing import List, Dict, Any
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

STYLE_PRESETS = {
    "manga": "manga style, detailed ink drawing, black and white with dramatic shading, high contrast, Japanese manga art, graphic novel visual",
    "anime": "anime style, vibrant colors, detailed character design, Studio Ghibli quality, beautiful fantasy lighting, masterwork anime key visual",
    "cinematic": "cinematic style, dramatic movie still, professional color grading, anamorphic lens flare, award-winning cinematography, highly detailed",
    "realistic": "photorealistic, professional photography, sharp focus, natural lighting, 8k uhd, dslr, hyperrealistic detail",
    "fantasy": "fantasy art style, magical atmosphere, ethereal lighting, vibrant colors, epic fantasy illustration, highly detailed",
    "dark": "dark moody atmosphere, gothic style, deep shadows, dramatic chiaroscuro lighting, ominous tone, highly detailed"
}

async def extract_main_character(story_text: str, ollama_url: str = 'http://localhost:11434', model: str = 'qwen2.5:3b', log_callback=None) -> str:
    """Extracts a short, reusable visual description of the story's main subject/character."""
    prompt = (
        "Describe the main character or subject of this story in ONE short visual sentence "
        "(appearance, species, clothing, distinguishing features). No preamble, no quotes.\n\n"
        f"STORY:\n{story_text[:2000]}"
    )
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url.rstrip('/')}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}}
            )
            if response.status_code == 200:
                desc = response.json().get("response", "").strip().replace('"', '').replace('**', '')
                desc = desc.split("\n")[0].strip()
                if desc:
                    if log_callback:
                        log_callback("success", f"[PROMPTER] Main subject: '{desc[:80]}...'")
                    return desc
    except Exception as e:
        logger.warning(f"Main character extraction failed: {e}")
    if log_callback:
        log_callback("warning", "[PROMPTER] Could not extract main subject, using scene descriptions as-is.")
    return "the main subject of the scene"

async def generate_prompts(scenes: List[Dict[str, Any]], style: str = 'manga', ollama_url: str = 'http://localhost:11434', model: str = 'qwen2.5:3b', story_text: str = '', log_callback=None) -> List[Dict[str, Any]]:
    """Converts a list of scene visual descriptions into highly detailed image generation prompts using Ollama."""
    style_preset = STYLE_PRESETS.get(style.lower(), STYLE_PRESETS["manga"])
    enhanced_scenes = []

    if log_callback:
        log_callback("info", f"[PROMPTER] Expanding {len(scenes)} scenes with style '{style}' via Ollama...")

    # Identify the story's actual main character so every scene prompt stays faithful
    character_desc = await extract_main_character(story_text, ollama_url, model, log_callback) if story_text else "the main subject of the scene"

    for scene in scenes:
        scene_num = scene.get("scene_number", 1)
        desc = scene.get("description", "")

        if log_callback:
            log_callback("debug", f"[PROMPTER] Processing Scene {scene_num}: '{desc[:30]}...'")

        system_prompt = (
            f"You are an expert prompt engineer for generative AI models like Stable Diffusion.\n"
            f"Your job is to expand the given visual scene description into a highly detailed, descriptive, single-paragraph prompt optimized for generating a high-quality vertical portrait image (9:16 aspect ratio).\n"
            f"STYLE DIRECTION: {style_preset}.\n"
            f"CHARACTER CONSISTENCY: The story's main subject is: '{character_desc}'. Always depict this exact subject in every scene. Never replace it with a different character.\n"
            f"Focus on styling, subject, action, composition, camera shot type, lighting, textures, and color.\n"
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
        logger.info(f"Sending prompt request to Ollama for scene {scene_num}. URL: {url}, Model: {model}")
        
        image_prompt = ""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, json=payload)
                logger.info(f"Ollama response received for scene {scene_num}. Status: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    image_prompt = result.get("response", "").strip()
                else:
                    logger.error(f"Ollama prompt generator returned status {response.status_code}: {response.text}")
                    if log_callback:
                        log_callback("error", f"[PROMPTER] API error for scene {scene_num}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error calling Ollama prompt generator for scene {scene_num}: {str(e)}")
            if log_callback:
                log_callback("warning", f"[PROMPTER] Scene {scene_num} expansion failed: {str(e)}")

        # Fallback if Ollama fails or is unreachable
        if not image_prompt:
            logger.info(f"Using fallback prompt for scene {scene_num}")
            if log_callback:
                log_callback("info", f"[PROMPTER] Scene {scene_num} using basic fallback.")
            # Ensure the fallback is at least somewhat descriptive and includes the style
            image_prompt = f"{desc}"
            if "Cinematic scene showing:" not in image_prompt and "Visual representation of:" not in image_prompt:
                 image_prompt = f"Cinematic visual of: {image_prompt}"
            image_prompt = f"{image_prompt}, {style_preset}"
        else:
            if log_callback:
                log_callback("success", f"[PROMPTER] Scene {scene_num} prompt expanded ({len(image_prompt)} chars).")

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
