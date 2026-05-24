import sqlite3
import aiosqlite
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

class Database:
    def __init__(self, db_path: Path = settings.database_path):
        self.db_path = db_path

    async def init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            # Projects Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    story_text TEXT NOT NULL,
                    style TEXT DEFAULT 'manga',
                    status TEXT DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # Scenes Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    image_prompt TEXT,
                    negative_prompt TEXT,
                    image_path TEXT,
                    narration_text TEXT NOT NULL,
                    audio_path TEXT,
                    duration REAL DEFAULT 0.0,
                    animation_type TEXT,
                    video_path TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            # Migration: Check if negative_prompt exists in scenes
            try:
                async with db.execute("SELECT negative_prompt FROM scenes LIMIT 1") as cursor:
                    await cursor.fetchone()
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                logger.info("Migrating database: adding negative_prompt column to scenes table.")
                await db.execute("ALTER TABLE scenes ADD COLUMN negative_prompt TEXT")
                await db.commit()
            # Jobs Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    job_type TEXT DEFAULT 'single',
                    status TEXT DEFAULT 'queued',
                    progress REAL DEFAULT 0.0,
                    current_step TEXT DEFAULT 'pending',
                    log TEXT DEFAULT '',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            await db.commit()

    async def get_db(self):
        return await aiosqlite.connect(self.db_path)

db_manager = Database()

# Helper to format rows as dict
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# CRUD helper functions

async def create_project(title: str, story_text: str, style: str = 'manga') -> Dict[str, Any]:
    project_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        await db.execute(
            "INSERT INTO projects (id, title, story_text, style, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, title, story_text, style, 'draft', now, now)
        )
        await db.commit()
        async with db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)) as cursor:
            return await cursor.fetchone()

async def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        async with db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)) as cursor:
            project = await cursor.fetchone()
            if project:
                project['scenes'] = await get_scenes(project_id)
            return project

async def list_projects() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        async with db.execute("SELECT * FROM projects ORDER BY created_at DESC") as cursor:
            return await cursor.fetchall()

async def delete_project(project_id: str):
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()

async def update_project(project_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    if not kwargs:
        return await get_project(project_id)
    
    kwargs['updated_at'] = datetime.utcnow().isoformat()
    keys = list(kwargs.keys())
    values = list(kwargs.values())
    set_clause = ", ".join([f"{k} = ?" for k in keys])
    values.append(project_id)
    
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
        await db.commit()
    return await get_project(project_id)

async def create_scene(project_id: str, scene_number: int, description: str, narration_text: str, image_prompt: str = None) -> Dict[str, Any]:
    scene_id = str(uuid.uuid4())
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        await db.execute(
            "INSERT INTO scenes (id, project_id, scene_number, description, image_prompt, narration_text) VALUES (?, ?, ?, ?, ?, ?)",
            (scene_id, project_id, scene_number, description, image_prompt, narration_text)
        )
        await db.commit()
        async with db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)) as cursor:
            return await cursor.fetchone()

async def get_scenes(project_id: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        async with db.execute("SELECT * FROM scenes WHERE project_id = ? ORDER BY scene_number ASC", (project_id,)) as cursor:
            return await cursor.fetchall()

async def update_scene(scene_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    if not kwargs:
        return
    keys = list(kwargs.keys())
    values = list(kwargs.values())
    set_clause = ", ".join([f"{k} = ?" for k in keys])
    values.append(scene_id)
    
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        await db.execute(f"UPDATE scenes SET {set_clause} WHERE id = ?", values)
        await db.commit()
        async with db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)) as cursor:
            return await cursor.fetchone()

async def create_job(project_id: str, job_type: str = 'single') -> Dict[str, Any]:
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        await db.execute(
            "INSERT INTO jobs (id, project_id, job_type, status, progress, current_step, log, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, project_id, job_type, 'queued', 0.0, 'pending', '', now)
        )
        await db.commit()
        async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
            return await cursor.fetchone()

async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
            return await cursor.fetchone()

async def get_jobs_by_project(project_id: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        async with db.execute("SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at DESC", (project_id,)) as cursor:
            return await cursor.fetchall()

async def update_job(job_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    if not kwargs:
        return await get_job(job_id)
    
    if kwargs.get('status') in ['done', 'failed']:
        kwargs['completed_at'] = datetime.utcnow().isoformat()
        
    keys = list(kwargs.keys())
    values = list(kwargs.values())
    set_clause = ", ".join([f"{k} = ?" for k in keys])
    values.append(job_id)
    
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        await db.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
        await db.commit()
    return await get_job(job_id)

async def append_job_log(job_id: str, log_line: str):
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        async with db.execute("SELECT log FROM jobs WHERE id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            current_log = row['log'] if row else ''
        
        new_log = current_log + log_line + "\n"
        await db.execute("UPDATE jobs SET log = ? WHERE id = ?", (new_log, job_id))
        await db.commit()

async def get_queued_jobs() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = dict_factory
        async with db.execute("SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at ASC") as cursor:
            return await cursor.fetchall()
