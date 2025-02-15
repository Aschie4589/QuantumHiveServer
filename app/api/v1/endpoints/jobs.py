from fastapi import APIRouter, Depends, HTTPException, Form, Body, Query
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.db.base import get_db
from app.schemas.job import JobBase, JobStatusModel, JobCreate, JobRequestModel
from app.models.job import JobStatus

from app.core.job_manager import job_manager


router = APIRouter()

@router.get("/status/")
def get_job_status(job_id = Query(...), current_user: dict = Depends(get_current_user), response_model = JobStatusModel):
    # Check that the job is assigned to the user
    j = job_manager.get_job_status(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found.")
    uid = job_manager.get_assigned_worker(job_id)
    if not uid:
        raise HTTPException(status_code=404, detail="Job not assigned to any worker.")
    if uid["id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Unauthorized user.")
    
    # user is authorized.
    return {
        "job_id": j["id"],
        "job_status": j["status"]
    }

@router.get("/ping")
def ping(current_user: dict = Depends(get_current_user)):
    # Update the last ping time for the worker
    j = job_manager.ping_worker(current_user["sub"])
    if not j:
        raise HTTPException(status_code=400, detail="Worker not found.")
    return {"message": "pong"}

@router.get("/request")
def request_job(current_user: dict = Depends(get_current_user), response_model = JobRequestModel):
    print("Requesting job for user:", current_user["sub"])
    j = job_manager.assign_job_to_worker(current_user["sub"])
    if not j:
        print("No job available.")
        raise HTTPException(status_code=400, detail="No job available.")
    
    # If job is available, return all info about the job that the user might need to complete it. 
    # For example, kraus id and vector id.
    # TODO: implement
    print("Assigned job:", j)
    return {
        "job_id": j.id,
        "job_type": j.job_type,
        "job_data": j.input_data,
        "job_status": j.status,
        "kraus_id": j.kraus_operator,
        "vector_id": j.vector
    }

@router.post("/pause")
def pause_job(job_id: str = Form(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check that the job is assigned to the user
    j = job_manager.get_job_status(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found.")
    uid = job_manager.get_assigned_worker(job_id)
    if not uid:
        raise HTTPException(status_code=404, detail="Job not assigned to any worker.")
    if uid["id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Unauthorized user.")
    
    # user is authorized.
    # check that the job was running
    if j["status"] != "running":
        raise HTTPException(status_code=400, detail="Job is not running.")
    
    # mark the job as paused
    j = job_manager.update_job_status(job_id, JobStatus.paused)
    if not j:
        raise HTTPException(status_code=400, detail="Job pausing failed.")
    return {"result": "success"}

@router.post("/resume")
def resume_job(job_id: str = Form(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check that the job is assigned to the user
    j = job_manager.get_job_status(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found.")
    uid = job_manager.get_assigned_worker(job_id)
    if not uid:
        raise HTTPException(status_code=404, detail="Job not assigned to any worker.")
    if uid["id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Unauthorized user.")
    
    # user is authorized.
    # check that the job was paused
    if j["status"] != "paused":
        raise HTTPException(status_code=400, detail="Job is not paused.")
    
    # mark the job as resumed
    j = job_manager.update_job_status(job_id, JobStatus.running)
    if not j:
        raise HTTPException(status_code=400, detail="Job resuming failed.")
    return {"result": "success"}

@router.post("/create")
def create_job(job: JobCreate = Body(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db), response_model = JobBase):
    # Debug: print all job info
    print("Creating job for user:", current_user["sub"])
    print(f"Job type: -{job.job_type}-")
    print("Input data:", job.input_data)
    print("Kraus operator:", job.kraus_operator)
    print("Vector:", job.vector)
    # Create a new job
    j = job_manager.create_job(job.job_type, job.input_data, job.kraus_operator, job.vector)
    if not j:
        raise HTTPException(status_code=400, detail="Job creation failed.")
    # Debug info
    print("Job created:", j)

    response={
        "job_id": j.id
    }
    return response
@router.post("/update-iterations")
def update_iterations(job_id: str = Form(...), num_iterations: int = Form(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check that the job is assigned to the user
    j = job_manager.get_job_status(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found.")
    uid = job_manager.get_assigned_worker(job_id)
    if not uid:
        raise HTTPException(status_code=404, detail="Job not assigned to any worker.")
    if uid["id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Unauthorized user.")
    
    # user is authorized.
    # update the number of iterations
    j = job_manager.update_iterations(job_id, num_iterations)
    if not j:
        raise HTTPException(status_code=400, detail="Job iteration update failed.")
    return {"result": "success"}

@router.post("/complete")
def complete_job(job_id: str = Form(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check that the job is assigned to the user
    j = job_manager.get_job_status(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found.")
    uid = job_manager.get_assigned_worker(job_id)
    if not uid:
        raise HTTPException(status_code=404, detail="Job not assigned to any worker.")
    if uid["id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Unauthorized user.")
    
    # user is authorized.
    # check that the job was running
    if j["status"] != "running":
        raise HTTPException(status_code=400, detail="Job is not running.")
    
    # check that the user has uploaded the required files
    # if the job is create kraus, check that the kraus file is uploaded    
    jtype = job_manager.get_job_type(job_id)
    if not jtype:
        raise HTTPException(status_code=404, detail="Job type not found.")

    if jtype["job_type"] == "generate_kraus":
        jkraus = job_manager.get_kraus_operator(job_id)
        if not jkraus:
            raise HTTPException(status_code=404, detail="Kraus operator not found.")
        if not jkraus["kraus_operator"]:
            raise HTTPException(status_code=400, detail="Kraus operator file not uploaded.")

    # if the job is create vector, check that the vector file is uploaded
    if jtype["job_type"] == "generate_vector":
        jvector = job_manager.get_vector(job_id)
        if not jvector:
            raise HTTPException(status_code=404, detail="Vector not found.")
        if not jvector["vector"]:
            raise HTTPException(status_code=400, detail="Vector file not uploaded.")

    # if the job type is minimize, both fields are populated from start. Don't do any checks
    # TODO : find some reasonable checks

    # mark the job as completed
    j = job_manager.complete_job(job_id)
    if not j:
        raise HTTPException(status_code=400, detail="Job completion failed.")
    return {"result": "success"}

@router.post("/cancel")
def cancel_job(job_id: str = Form(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check that the job is assigned to the user
    j = job_manager.get_job_status(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found.")
    uid = job_manager.get_assigned_worker(job_id)
    if not uid:
        raise HTTPException(status_code=404, detail="Job not assigned to any worker.")
    if uid["id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Unauthorized user.")
    
    # user is authorized.
    # check that the job was running
    if j["status"] != "running" and j["status"] != "paused":
        raise HTTPException(status_code=400, detail="Job is not running or paused.")
    
    # mark the job as canceled
    j = job_manager.update_job_status(job_id, JobStatus.canceled)
    if not j:
        raise HTTPException(status_code=400, detail="Job cancel failed.")
    return {"result": "success"}

