from app import app
# Import and include your routers
from app.api.v1.endpoints import users, auth, jobs, downloads
from fastapi.middleware.cors import CORSMiddleware
from app.core.job_manager import job_manager
from app.db.base import engine, Base
from app.models.job import JobType, JobStatus

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(downloads.router, prefix="/files", tags=["jobs"])



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


@app.get("/startup")
def do_startup():
    # Add a dummy job
    print("Adding a dummy job")
    j = job_manager.create_job(JobType.minimize, {"dummy": "data"}, "dummy_kraus", "dummy_vector")
    print(j)
    id = int(j.id)
    print("Job ID:", id)
    print("New job:", j)
    return {"message": "Startup completed"}


# Run with: uvicorn app.main:app --host 0.0.0.0 --port 8000