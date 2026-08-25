import asyncio
import threading
import logging
import traceback
from queue import Queue, Empty
from datetime import datetime, timezone
import sqlite3
from typing import Callable, Dict, List, Any
from backend.database.db import update_job, append_job_log

logger = logging.getLogger(__name__)

class JobQueue:
    def __init__(self):
        self._queue = Queue()
        self._worker_thread = None
        self._running = False
        self.loop = None  # Reference to the main asyncio loop
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._subscribers_lock = threading.Lock()

    def set_loop(self, loop):
        self.loop = loop

    def start(self):
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="JobQueueWorker")
        self._worker_thread.start()
        logger.info("JobQueue background worker thread started.")

    def stop(self):
        self._running = False
        # Push a sentinel to break the block
        self._queue.put(None)
        if self._worker_thread:
            self._worker_thread.join(timeout=3.0)
        logger.info("JobQueue background worker thread stopped.")

    def submit_job(self, job_id: str, project_id: str, func: Callable, *args, **kwargs):
        """Pushes a job into the queue."""
        logger.info(f"Submitting job {job_id} to background queue.")
        self._queue.put({
            "job_id": job_id,
            "project_id": project_id,
            "func": func,
            "args": args,
            "kwargs": kwargs
        })

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """Subscribes an asyncio SSE queue to a specific job's progress updates."""
        q = asyncio.Queue()
        with self._subscribers_lock:
            if job_id not in self._subscribers:
                self._subscribers[job_id] = []
            self._subscribers[job_id].append(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue):
        with self._subscribers_lock:
            if job_id in self._subscribers:
                try:
                    self._subscribers[job_id].remove(q)
                    if not self._subscribers[job_id]:
                        del self._subscribers[job_id]
                except ValueError:
                    pass

    def emit_progress(self, job_id: str, step: str, progress: float, message: str = ""):
        """Sends progress update to database and all active asyncio SSE streams."""
        # 1. Update database synchronously via a thread-safe helper
        log_line = f"[{step.upper()} - {int(progress * 100)}%] {message}"
        logger.info(f"Job {job_id[:8]} progress: {log_line}")
        
        self._sync_db_update(
            "UPDATE jobs SET progress = ?, current_step = ?, log = log || ? || '\n' WHERE id = ?",
            (progress, step, log_line, job_id)
        )

        # 2. Dispatch event to asyncio queues
        event = {
            "type": "progress",
            "job_id": job_id,
            "step": step,
            "progress": progress,
            "message": message
        }
        self._dispatch_event(job_id, event)

    def emit_log(self, job_id: str, level: str, message: str):
        """Sends a detailed low-level engine log to the frontend terminal."""
        event = {
            "type": "log",
            "job_id": job_id,
            "level": level,
            "message": message
        }
        self._dispatch_event(job_id, event)

    def _dispatch_event(self, job_id: str, event: dict):
        """Helper to dispatch events to SSE subscribers."""
        with self._subscribers_lock:
            if job_id in self._subscribers:
                for q in self._subscribers[job_id]:
                    if self.loop:
                        self.loop.call_soon_threadsafe(q.put_nowait, event)

    def _sync_db_update(self, query: str, params: tuple):
        """Helper to perform thread-safe synchronous updates to SQLite."""
        try:
            from backend.config import get_settings
            db_path = get_settings().database_path
            with sqlite3.connect(db_path) as conn:
                conn.execute(query, params)
                conn.commit()
        except Exception as e:
            logger.error(f"Database sync update failed: {e}")

    def _worker_loop(self):
        """Worker thread loop consuming jobs sequentially to respect RAM."""
        while self._running:
            try:
                # Wait for job with a timeout so we can check if thread stopped
                job_data = self._queue.get(timeout=2.0)
                if job_data is None:
                    # Stopped sentinel
                    break
                    
                job_id = job_data["job_id"]
                project_id = job_data["project_id"]
                func = job_data["func"]
                args = job_data["args"]
                kwargs = job_data["kwargs"]
                
                logger.info(f"Worker thread starting job {job_id} for project {project_id}")
                
                # Update status to running
                now = datetime.now(timezone.utc).isoformat()
                self._sync_db_update("UPDATE jobs SET status = 'running' WHERE id = ?", (job_id,))
                self._sync_db_update("UPDATE projects SET status = 'generating' WHERE id = ?", (project_id,))

                # Create progress and log callbacks
                def progress_cb(step: str, progress: float, msg: str = ""):
                    self.emit_progress(job_id, step, progress, msg)
                
                def log_cb(level: str, msg: str):
                    self.emit_log(job_id, level, msg)

                # Execute
                try:
                    # Run the async pipeline function on a new dedicated event loop in this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Run the async pipeline to completion
                    # Pass log_callback to kwargs
                    kwargs['log_callback'] = log_cb
                    loop.run_until_complete(func(project_id, job_id, progress_cb, **kwargs))
                    loop.close()
                    
                    # Complete
                    logger.info(f"Worker thread successfully finished job {job_id}")
                    now = datetime.now(timezone.utc).isoformat()
                    self._sync_db_update("UPDATE jobs SET status = 'done', progress = 1.0, completed_at = ? WHERE id = ?", (now, job_id))
                    self._sync_db_update("UPDATE projects SET status = 'completed' WHERE id = ?", (project_id,))
                    self.emit_progress(job_id, "completed", 1.0, "Video generation pipeline finished successfully!")
                    
                except Exception as run_err:
                    import traceback
                    err_msg = "".join(traceback.format_exception(type(run_err), run_err, run_err.__traceback__))
                    logger.error(f"Job {job_id} failed with error:\n{err_msg}")
                    
                    from backend.config import get_settings
                    db_path = get_settings().database_path
                    with sqlite3.connect(db_path) as conn:
                        now = datetime.now(timezone.utc).isoformat()
                        conn.execute(
                            "UPDATE jobs SET status = 'failed', error = ?, completed_at = ? WHERE id = ?",
                            (str(run_err), now, job_id)
                        )
                        conn.execute("UPDATE projects SET status = 'failed' WHERE id = ?", (project_id,))
                        conn.commit()
                        
                    self.emit_progress(job_id, "failed", 1.0, f"Pipeline crashed: {str(run_err)}")
                    
                finally:
                    self._queue.task_done()
                    
            except Empty:
                continue
            except Exception as outer_err:
                logger.error(f"Outer exception in worker loop: {outer_err}")

# Global JobQueue
job_queue = JobQueue()
