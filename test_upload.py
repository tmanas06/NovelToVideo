import httpx
import sys
from pathlib import Path

async def test_upload():
    comfyui_url = "http://127.0.0.1:8188"
    image_path = Path("/home/manas/Desktop/StoryToReel/assets/fonts/Inter-Bold.ttf") # Just a dummy file
    async with httpx.AsyncClient() as client:
        with open(image_path, "rb") as f:
            up_resp = await client.post(f"{comfyui_url}/upload/image", files={"image": (image_path.name, f)})
            print(up_resp.json())

import asyncio
asyncio.run(test_upload())
