import json
import logging
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.workers.queue_manager import job_queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])

@router.get("/{job_id}")
async def stream_progress(job_id: str):
    """Establishes an SSE connection to broadcast live pipeline events."""
    
    async def event_generator():
        logger.info(f"SSE client connected to monitor job {job_id[:8]}")
        # Subscribe to updates
        q = job_queue.subscribe(job_id)
        
        try:
            # Send initial ping/connection check
            yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"
            
            while True:
                try:
                    # Wait for next progress event from worker thread
                    # Use a short timeout so we periodically check if connection is active
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    
                    yield f"event: progress\ndata: {json.dumps(event)}\n\n"
                    
                    if event.get("step") == "completed" or event.get("step") == "failed":
                        break
                        
                    q.task_done()
                except asyncio.TimeoutError:
                    # Connection keep-alive ping
                    yield "event: ping\ndata: {}\n\n"
        except asyncio.CancelledError:
            logger.info(f"SSE client disconnected from job {job_id[:8]}")
        finally:
            # Ensure cleanup
            job_queue.unsubscribe(job_id, q)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
