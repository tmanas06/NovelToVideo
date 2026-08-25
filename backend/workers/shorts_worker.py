import logging
import asyncio
import httpx
import json
import uuid
import random
import subprocess
import shutil
from pathlib import Path
from backend.config import get_settings, PROJECT_ROOT
from backend.utils.log_handler import log_queue
from backend.services.image_generator import generate_image

logger = logging.getLogger(__name__)
settings = get_settings()

async def log(message: str, level: str = "info"):
    log_queue.put(f"[{level.upper()}] {message}")
    logger.info(message)

async def run_shorts_pipeline(job_id: str, prompt: str, duration: int, image_path: str = None):
    """Executes the pipeline in two sequential steps to save memory."""
    try:
        logger.info(f"Shorts Pipeline [{job_id}] STARTED.")
        comfyui_url = settings.comfyui_url.rstrip('/')
        
        # Step 1: Generate/Prepare Base Image
        if not image_path:
            await log("Generating base image...", "info")
            img_dir = PROJECT_ROOT / "temp" / job_id / "images"
            img_dir.mkdir(parents=True, exist_ok=True)
            target_img_path = img_dir / "base_image.png"
            image_path_obj = await generate_image(
                prompt=prompt,
                negative_prompt="distorted face, extra paws, blurry",
                output_path=target_img_path,
                mode="comfyui",
                width=512,
                height=768,
                comfyui_url=comfyui_url
            )
            image_path = str(image_path_obj)
            await log(f"Base image ready: {image_path}", "info")

        # Step 2: LTX Video Generation
        await log("Loading LTX Video model and generating video...", "info")
        
        async with httpx.AsyncClient(timeout=3600.0) as client:
            # Upload image
            with open(image_path, "rb") as f:
                up_resp = await client.post(f"{comfyui_url}/upload/image", files={"image": (Path(image_path).name, f)})
            
            if up_resp.status_code != 200:
                await log("Image upload failed.", "error")
                return
            
            uploaded_file = up_resp.json().get("name")
            
            # Define LTX-2B Workflow
            workflow = {
                "10": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "ltx-video-2b-v0.9.5.safetensors"}},
                "11": {"class_type": "CLIPLoader", "inputs": {"clip_name": "t5xxl_fp16.safetensors", "type": "ltxv"}},
                "12": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["11", 0]}},
                "13": {"class_type": "CLIPTextEncode", "inputs": {"text": "distorted face", "clip": ["11", 0]}},
                "14": {"class_type": "LoadImage", "inputs": {"image": uploaded_file}},
                "15": {"class_type": "LTXVImgToVideo", "inputs": {"positive": ["12", 0], "negative": ["13", 0], "vae": ["10", 2], "image": ["14", 0], "width": 512, "height": 768, "length": 49, "batch_size": 1, "strength": 1.0}},
                "16": {"class_type": "KSampler", "inputs": {"seed": random.randint(1, 1000000000), "steps": 12, "cfg": 3.0, "sampler_name": "euler", "scheduler": "karras", "denoise": 1.0, "model": ["10", 0], "positive": ["15", 0], "negative": ["15", 1], "latent_image": ["15", 2]}},
                "17": {"class_type": "VAEDecode", "inputs": {"samples": ["16", 0], "vae": ["10", 2]}},
                "18": {"class_type": "CreateVideo", "inputs": {"images": ["17", 0], "fps": 8.0}},
                "19": {"class_type": "SaveVideo", "inputs": {"video": ["18", 0], "filename_prefix": f"short_{job_id}", "format": "mp4", "codec": "h264"}}
            }
        
            # Submit video generation
            resp = await client.post(f"{comfyui_url}/prompt", json={"prompt": workflow, "client_id": job_id})
            if resp.status_code != 200:
                await log(f"Prompt submission failed: {resp.status_code} - {resp.text}", "error")
                return
            
            prompt_id = resp.json().get("prompt_id")
            await log(f"Prompt submitted successfully. ID: {prompt_id}", "info")
            
            # Wait for completion (polls history)
            await log(f"Workflow queued. ID: {prompt_id}. Waiting for completion...", "info")
            
            # Poll for status
            max_attempts = 600
            output_video_path = None
            
            for attempt in range(max_attempts):
                await asyncio.sleep(10)
                try:
                    history_resp = await client.get(f"{comfyui_url}/history/{prompt_id}")
                    if history_resp.status_code == 200:
                        history = history_resp.json()
                        if prompt_id in history:
                            outputs = history[prompt_id].get("outputs", {})
                            for node_id, node_output in outputs.items():
                                if "videos" in node_output:
                                    video_info = node_output["videos"][0]
                                    filename = video_info.get("filename")
                                    subfolder = video_info.get("subfolder", "")
                                    view_url = f"{comfyui_url}/view?filename={filename}&subfolder={subfolder}&type=output"
                                    video_data = await client.get(view_url)
                                    if video_data.status_code == 200:
                                        output_video_path = PROJECT_ROOT / "outputs" / f"short_{job_id}_raw.mp4"
                                        output_video_path.parent.mkdir(parents=True, exist_ok=True)
                                        with open(output_video_path, "wb") as f:
                                            f.write(video_data.content)
                                        await log(f"Video downloaded: {output_video_path}", "success")
                                        break
                            if output_video_path: break
                except Exception as e:
                    logger.warning(f"Error polling history: {e}")
            
            if not output_video_path:
                await log("Generation timed out or failed.", "error")
                return

            # STEP 7: Mix audio
            await log("Mixing audio...", "info")
            audio_path = PROJECT_ROOT / "assets" / "backgrounds" / "audio" / "placeholder_audio.wav"
            final_output = PROJECT_ROOT / "outputs" / f"short_{job_id}_final.mp4"
            
            ffmpeg_cmd = ["ffmpeg", "-y", "-i", str(output_video_path), "-i", audio_path, "-map", "0:v:0", "-map", "1:a:0", "-shortest", "-c:v", "copy", "-c:a", "aac", str(final_output)]
            process = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await process.communicate()
            
            if process.returncode == 0:
                await log(f"Short generated successfully: {final_output.name}", "success")
            else:
                await log("Audio mixing failed.", "error")

    except Exception as e:
        logger.exception(f"CRITICAL ERROR: {str(e)}")
        await log(f"CRITICAL ERROR: {str(e)}", "error")
