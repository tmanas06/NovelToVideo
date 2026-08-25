import asyncio
import json
import httpx
import uuid
import sys
from pathlib import Path

async def test_shorts_pipeline():
    prompt = "Cute chubby orange cat eating ramen noodles, adorable expression, chewing motion, animated style, cozy kitchen background, smooth movement, high detail"
    duration = 5
    job_id = f"test_{uuid.uuid4().hex[:8]}"
    
    print(f"Testing shorts pipeline with job_id: {job_id}")
    
    # We can call the worker function directly
    from backend.workers.shorts_worker import run_shorts_pipeline
    from backend.utils.log_handler import log_queue
    
    # Task to print logs
    async def print_logs():
        while True:
            while not log_queue.empty():
                print(log_queue.get())
            await asyncio.sleep(1)

    log_task = asyncio.create_task(print_logs())
    
    # This will run the pipeline and we can see logs
    try:
        await run_shorts_pipeline(job_id, prompt, duration)
    finally:
        log_task.cancel()
        # Final drain
        while not log_queue.empty():
            print(log_queue.get())

if __name__ == "__main__":
    # Add project root to path
    sys.path.append("/home/manas/Desktop/StoryToReel")
    asyncio.run(test_shorts_pipeline())
