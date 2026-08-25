import uuid
import logging
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from backend.workers.shorts_worker import run_shorts_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/shorts", tags=["shorts"])

class ShortRequest(BaseModel):
    prompt: str
    duration: int
    image_path: str | None = None

@router.post("/generate")
async def generate_short(request: ShortRequest):
    logger.info(f"Received request for short generation: {request}")
    job_id = str(uuid.uuid4())
    logger.info(f"Queuing short video generation job {job_id} for prompt: {request.prompt[:30]}...")
    
    try:
        # Directly create task to ensure execution
        task = asyncio.create_task(run_shorts_pipeline(job_id, request.prompt, request.duration, request.image_path))
        logger.info(f"Task created successfully via asyncio.create_task: {task}")
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return {"error": str(e)}, 500
    
    return {"job_id": job_id, "message": "Short generation queued"}
