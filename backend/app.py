import logging
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path("/home/manas/Desktop/StoryToReel/temp/app.log"), mode="a")
    ]
)
logger = logging.getLogger(__name__)

# Import DB and Queue managers
from backend.database.db import db_manager
from backend.workers.queue_manager import job_queue
from backend.routes import projects, generation, batch, settings, sse

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Initializing database schema...")
    await db_manager.init_db()
    
    # Pass running event loop to the job queue
    logger.info("Starting background worker queue...")
    job_queue.set_loop(asyncio.get_running_loop())
    job_queue.start()
    
    yield
    
    # Shutdown tasks
    logger.info("Stopping background worker queue...")
    job_queue.stop()

app = FastAPI(
    title="StoryToReel AI",
    description="Automated Story to Vertical Video Generator",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router)
app.include_router(generation.router)
app.include_router(batch.router)
app.include_router(settings.router)
app.include_router(sse.router)

# Mount outputs and temp directories for viewing assets
outputs_dir = Path("/home/manas/Desktop/StoryToReel/outputs")
temp_dir = Path("/home/manas/Desktop/StoryToReel/temp")
outputs_dir.mkdir(parents=True, exist_ok=True)
temp_dir.mkdir(parents=True, exist_ok=True)

app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")
app.mount("/temp", StaticFiles(directory=str(temp_dir)), name="temp")

# Mount frontend files at the root
frontend_dir = Path("/home/manas/Desktop/StoryToReel/frontend")
frontend_dir.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
