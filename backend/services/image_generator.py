import httpx
import json
import logging
import random
import uuid
import asyncio
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Dict, Any
from backend.config import get_settings
from backend.utils.file_utils import get_project_images_dir

logger = logging.getLogger(__name__)
settings = get_settings()

def generate_placeholder_image(text: str, output_path: Path, width: int = 1080, height: int = 1920) -> Path:
    """Generates a beautiful gradient background image with overlaid scene text for robust fallbacks."""
    logger.info(f"Generating placeholder image for: {text[:30]}...")
    
    # Deterministic colors based on text hash for variety
    import hashlib
    text_hash = int(hashlib.md5(text.encode()).hexdigest(), 16)
    hue = text_hash % 360
    
    # Convert HSL to RGB for top color
    import colorsys
    rgb = colorsys.hls_to_rgb(hue / 360, 0.4, 0.7)
    top_color = (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
    bottom_color = (15, 15, 20)  # Always keep dark bottom for consistency
    
    # Create base image
    base = Image.new('RGB', (width, height), color=bottom_color)
    
    # Draw gradient
    draw = ImageDraw.Draw(base)
    for y in range(height):
        # Linear interpolation
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    # Draw decorative circles/glow
    glow = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([width//4, height//3, width*3//4, height*2//3], fill=(top_color[0], top_color[1], top_color[2], 40))
    base.paste(glow, mask=glow.split()[3])
    
    # Blur slightly for smooth glow
    base = base.filter(ImageFilter.GaussianBlur(5))
    draw = ImageDraw.Draw(base)
    
    # Draw nice grid or borders
    draw.rectangle([20, 20, width-20, height-20], outline=(124, 92, 252, 60), width=4)
    
    # Draw text
    font_path = Path("/home/manas/Desktop/StoryToReel/assets/fonts/Inter-Bold.ttf")
    if not font_path.exists():
        font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") # Fallback Linux font
        
    try:
        font = ImageFont.truetype(str(font_path), 40)
    except:
        font = ImageFont.load_default()
        
    # Wrap text to fit
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        # Check size of line
        test_line = " ".join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        if line_width > width - 120:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    # Render wrapped text centered
    total_text_height = sum([draw.textbbox((0,0), l, font=font)[3] - draw.textbbox((0,0), l, font=font)[1] for l in lines]) + (len(lines) - 1) * 15
    y_offset = (height - total_text_height) // 2
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x_offset = (width - w) // 2
        
        # Soft shadow
        draw.text((x_offset + 3, y_offset + 3), line, font=font, fill=(0, 0, 0, 150))
        # Main text
        draw.text((x_offset, y_offset), line, font=font, fill=(255, 255, 255))
        
        y_offset += h + 20
        
    # Brand logo overlay at the bottom
    try:
        sub_font = ImageFont.truetype(str(font_path.parent / "Inter-Regular.ttf"), 28)
    except:
        sub_font = ImageFont.load_default()
    brand_text = "STORYTOREEL AI"
    bbox = draw.textbbox((0,0), brand_text, font=sub_font)
    draw.text(((width - (bbox[2]-bbox[0]))//2, height - 100), brand_text, font=sub_font, fill=(124, 92, 252, 180))
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path, 'PNG')
    return output_path

async def generate_image(prompt: str, negative_prompt: str, output_path: Path, 
                         mode: str = 'comfyui', width: int = 1080, height: int = 1920,
                         comfyui_url: str = 'http://localhost:8188',
                         api_url: str = '', api_key: str = '',
                         log_callback=None) -> Path:
    """Generates a scene image via ComfyUI, API or beautiful placeholder fallback."""
    if mode.lower() == 'placeholder':
        if log_callback:
            log_callback("info", f"[IMAGEGEN] Using placeholder generator for prompt snippet: {prompt[:30]}...")
        return generate_placeholder_image(prompt.split(",")[0], output_path, width, height)

    if mode.lower() == 'comfyui':
        if log_callback:
            log_callback("info", f"[COMFYUI] Requesting image generation at {comfyui_url}...")
        client_id = str(uuid.uuid4())
        # ComfyUI prompt API format
        workflow = {
            # ... (workflow dict remains the same)
        }
        
        # Injecting actual workflow here (keeping previous code logic)
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": random.randint(1, 1000000000),
                    "steps": 14, # Optimized from 20 for faster laptop generation
                    "cfg": 7.0,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 768, # Reduced from 896 for speed; still looks good vertical
                    "batch_size": 1
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": f"storytoreel_{client_id}",
                    "images": ["8", 0]
                }
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Post generation request
                response = await client.post(f"{comfyui_url.rstrip('/')}/prompt", json={"prompt": workflow, "client_id": client_id})
                if response.status_code == 200:
                    res_json = response.json()
                    prompt_id = res_json.get("prompt_id")
                    if log_callback:
                        log_callback("debug", f"[COMFYUI] Prompt queued. ID: {prompt_id}. Polling for results...")
                    
                    # Poll for completion
                    for attempt in range(300): # Up to 10 minutes, but check more frequently
                        await asyncio.sleep(2) # Poll every 2 seconds instead of 5
                        history_response = await client.get(f"{comfyui_url.rstrip('/')}/history/{prompt_id}")
                        if history_response.status_code == 200:
                            history = history_response.json()
                            if prompt_id in history:
                                if log_callback:
                                    log_callback("success", f"[COMFYUI] Generation complete. Downloading image...")
                                # Completed! Extract filename
                                outputs = history[prompt_id].get("outputs", {})
                                for node_id, node_output in outputs.items():
                                    if "images" in node_output:
                                        for img_info in node_output["images"]:
                                            filename = img_info.get("filename")
                                            subfolder = img_info.get("subfolder", "")
                                            # Download image
                                            view_url = f"{comfyui_url.rstrip('/')}/view?filename={filename}&subfolder={subfolder}&type=output"
                                            img_data_res = await client.get(view_url)
                                            if img_data_res.status_code == 200:
                                                # Save temp image
                                                temp_path = output_path.parent / f"temp_{output_path.name}"
                                                with open(temp_path, "wb") as f:
                                                    f.write(img_data_res.content)
                                                
                                                # Upscale/Resize to 1080x1920
                                                with Image.open(temp_path) as img:
                                                    resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
                                                    output_path.parent.mkdir(parents=True, exist_ok=True)
                                                    resized_img.save(output_path, "PNG")
                                                    
                                                temp_path.unlink()
                                                logger.info(f"ComfyUI image generated successfully: {output_path}")
                                                if log_callback:
                                                    log_callback("success", f"[IMAGEGEN] Scene image saved and upscaled to 1080x1920.")
                                                return output_path
                        if attempt % 15 == 0 and log_callback: # Log every 30 seconds
                            log_callback("debug", f"[COMFYUI] Still processing... (attempt {attempt})")
                else:
                    err_body = response.text
                    logger.error(f"ComfyUI prompt failed (Status {response.status_code}): {err_body}")
                    if log_callback:
                        log_callback("error", f"[COMFYUI] Request failed ({response.status_code}): {err_body[:100]}...")
        except Exception as e:
            logger.error(f"Error communicating with ComfyUI: {e}")
            if log_callback:
                log_callback("error", f"[COMFYUI] Connection error: {str(e)}")

    elif mode.lower() == 'api' and api_url:
        if log_callback:
            log_callback("info", f"[IMAGEGEN] Calling external API: {api_url}...")
        # Fallback to an external API (e.g. HuggingFace, Stability AI, etc.)
        try:
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(api_url, json=payload, headers=headers)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    if log_callback:
                        log_callback("success", f"[IMAGEGEN] API image received and saved.")
                    return output_path
                elif log_callback:
                    log_callback("error", f"[IMAGEGEN] API returned {response.status_code}")
        except Exception as e:
            logger.error(f"Error calling external image API: {e}")
            if log_callback:
                log_callback("error", f"[IMAGEGEN] API connection failed: {str(e)}")

    # Solid fallback to placeholder
    if log_callback:
        log_callback("warning", f"[IMAGEGEN] Falling back to placeholder for scene.")
    return generate_placeholder_image(prompt.split(",")[0], output_path, width, height)

async def generate_images_for_project(scenes: List[Dict[str, Any]], project_id: str, log_callback=None, **kwargs) -> List[Dict[str, Any]]:
    """Helper to generate images sequentially for a project (to respect low RAM constraints)."""
    img_dir = get_project_images_dir(project_id)
    updated_scenes = []
    
    for scene in scenes:
        scene_num = scene.get("scene_number", 1)
        prompt = scene.get("image_prompt", "")
        neg_prompt = scene.get("negative_prompt", "")
        
        # If prompts aren't generated yet, create basic prompt using description
        if not prompt:
            prompt = scene.get("description", "A dramatic story scene")
            neg_prompt = "blurry, low quality"
            
        if log_callback:
            log_callback("info", f"[PIPELINE] Starting image generation for scene {scene_num}...")
            
        output_path = img_dir / f"scene_{scene_num:02d}.png"
        
        # Call single image generator with settings
        final_path = await generate_image(
            prompt=prompt,
            negative_prompt=neg_prompt,
            output_path=output_path,
            mode=kwargs.get("image_mode", settings.image_mode),
            width=kwargs.get("video_width", settings.video_width),
            height=kwargs.get("video_height", settings.video_height),
            comfyui_url=kwargs.get("comfyui_url", settings.comfyui_url),
            api_url=kwargs.get("image_api_url", settings.image_api_url),
            api_key=kwargs.get("image_api_key", settings.image_api_key),
            log_callback=log_callback
        )
        
        updated_scene = scene.copy()
        updated_scene["image_path"] = str(final_path)
        updated_scenes.append(updated_scene)
        
    return updated_scenes

