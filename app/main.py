from app import app
# Import and include your routers
from app.api.v1.endpoints import users, auth
from fastapi.middleware.cors import CORSMiddleware
from app.core.job_manager import job_manager
from app.db.base import engine, Base
from app.models.job import JobType, JobStatus

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router, prefix="/auth", tags=["jobs"])

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
    # Assign a worker
    print("Assigning the job to a worker")
    job_manager.assign_job_to_worker("worker1")
    # Get the assigned worker
    print("Assigned worker:", job_manager.get_assigned_worker(id))
    # Update the job status
    print("Updating the job status")
    job_manager.update_job_status(id, JobStatus.running)
    # Complete the job
    print("Completing the job")
    job_manager.complete_job(id, "dummy_result")
    # Get the job status
    print("Getting the job status")
    print(job_manager.get_job_status(id))
    # Restart the job
    print("Restarting the job")
    job_manager.restart_job(id)
    print("Job restarted")
    print(job_manager.get_job_status(id))
    # Update the Kraus operator
    print("Updating the Kraus operator")
    job_manager.update_kraus(id, "new_kraus")
    print(job_manager.get_job_status(id))
    # Update the vector
    print("Updating the vector")
    job_manager.update_vector(id, "new_vector")
    print(job_manager.get_job_status(id))
    # Update the number of iterations
    print("Updating the number of iterations")
    job_manager.update_iterations(id, 100)
    print(job_manager.get_job_status(id))
    return {"message": "Startup completed"}


# Run with: uvicorn app.main:app --host 0.0.0.0 --port 8000