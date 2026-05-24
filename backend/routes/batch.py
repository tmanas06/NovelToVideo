import uuid
from fastapi import APIRouter, HTTPException
from backend.models import BatchCreate, BatchResponse
from backend.database.db import create_project, create_job
from backend.workers.queue_manager import job_queue
from backend.workers.pipeline import run_pipeline

router = APIRouter(prefix="/api/batch", tags=["batch"])

@router.post("/", response_model=BatchResponse)
async def api_submit_batch(batch: BatchCreate):
    """Submits multiple stories at once, queuing them up sequentially in the background."""
    batch_id = str(uuid.uuid4())
    queued_jobs = []
    
    try:
        for idx, story in enumerate(batch.stories):
            # 1. Create project
            project = await create_project(
                title=story.title or f"Batch Story {idx+1}",
                story_text=story.story_text,
                style=story.style
            )
            
            # 2. Create job
            job = await create_job(project_id=project["id"], job_type="batch")
            
            # Submit to queue
            job_queue.submit_job(
                job_id=job["id"],
                project_id=project["id"],
                func=run_pipeline
            )
            
            queued_jobs.append(job)
            
        return {
            "batch_id": batch_id,
            "jobs": queued_jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
