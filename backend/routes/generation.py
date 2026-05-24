from fastapi import APIRouter, HTTPException
from backend.models import JobResponse
from backend.database.db import create_job, get_job, get_jobs_by_project, get_project
from backend.workers.queue_manager import job_queue
from backend.workers.pipeline import run_pipeline

router = APIRouter(prefix="/api/generate", tags=["generation"])

@router.post("/{project_id}", response_model=JobResponse)
async def start_generation(project_id: str):
    """Creates a video generation task and queues it for sequential background processing."""
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    try:
        # Create queued job entry in DB
        job = await create_job(project_id=project_id, job_type="single")
        
        # Submit to sequential executor thread
        job_queue.submit_job(
            job_id=job["id"],
            project_id=project_id,
            func=run_pipeline
        )
        
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/status", response_model=JobResponse)
async def get_generation_status(project_id: str):
    """Retrieves the status of the latest job for the specified project."""
    jobs = await get_jobs_by_project(project_id)
    if not jobs:
        raise HTTPException(status_code=404, detail="No generation jobs found for this project")
    return jobs[0]
