import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.utils.log_handler import log_queue

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("/stream")
async def stream_logs():
    """Streams system logs to the frontend."""
    async def log_generator():
        while True:
            if not log_queue.empty():
                log_msg = log_queue.get()
                yield f"data: {json.dumps({'message': log_msg})}\n\n"
            await asyncio.sleep(0.5)
            
    return StreamingResponse(log_generator(), media_type="text/event-stream")
