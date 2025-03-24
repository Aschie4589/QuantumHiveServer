# Import and include your routers
from app.api.v1.endpoints import users, auth, jobs, downloads, channels
from fastapi.middleware.cors import CORSMiddleware
from app.core.job_manager import job_manager
from app.db.base import engine, Base
from app.models.job import JobType, JobStatus
from app.core.channel_manager import channel_manager
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the background task."""
    print("Starting FastAPI app with background task...")
    
    # Start the background task
    channel_manager.task = asyncio.create_task(channel_manager.update())

    yield  # Let FastAPI start

    # Cleanup on shutdown
    print("Shutting down background task...")
    if channel_manager.task:
        channel_manager.task.cancel()
        try:
            await channel_manager.task
        except asyncio.CancelledError:
            print("Background task was cancelled")

app = FastAPI(title="QuantumHiveAPI", lifespan=lifespan)




app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(downloads.router, prefix="/files", tags=["jobs"])
app.include_router(channels.router, prefix="/channels", tags=["channels"])


# Create DB tables (if they don’t exist)
Base.metadata.create_all(bind=engine)

# CORS (Allow frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.get("/")
def read_root():
    return {"message": "QuantumHive API is running!"}


# Run with: uvicorn app.main:app --host 0.0.0.0 --port 8000