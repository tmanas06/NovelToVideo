import httpx
import json
import asyncio

async def check_node():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://127.0.0.1:8188/object_info")
            if resp.status_code == 200:
                info = resp.json()
                if "VHS_VideoCombine" in info:
                    print("VHS_VideoCombine found!")
                    print(json.dumps(info["VHS_VideoCombine"]["input"], indent=2))
                else:
                    print("VHS_VideoCombine NOT found!")
            else:
                print(f"Failed to get info: {resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_node())
