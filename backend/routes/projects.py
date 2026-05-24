from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from backend.models import ProjectCreate, ProjectResponse
from backend.database.db import create_project, get_project, list_projects, delete_project
from backend.utils.file_utils import cleanup_project_temp

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse)
async def api_create_project(project: ProjectCreate):
    try:
        new_project = await create_project(
            title=project.title,
            story_text=project.story_text,
            style=project.style
        )
        # Empty scenes list initially
        new_project["scenes"] = []
        return new_project
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[ProjectResponse])
async def api_list_projects():
    try:
        return await list_projects()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}", response_model=ProjectResponse)
async def api_get_project(project_id: str):
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.delete("/{project_id}")
async def api_delete_project(project_id: str, background_tasks: BackgroundTasks):
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        await delete_project(project_id)
        # Run directory cleanup in background tasks
        background_tasks.add_task(cleanup_project_temp, project_id)
        return {"status": "success", "message": f"Project {project_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
