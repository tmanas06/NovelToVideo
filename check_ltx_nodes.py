import httpx
import json
import asyncio

async def check_nodes():
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://127.0.0.1:8188/object_info")
        info = resp.json()
        for node in ["CreateVideo", "SaveVideo", "LTXVImgToVideo"]:
            print(f"--- {node} ---")
            print(json.dumps(info.get(node, {}).get("input", "NOT FOUND"), indent=2))

if __name__ == "__main__":
    asyncio.run(check_nodes())
