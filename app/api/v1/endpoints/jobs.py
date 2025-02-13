from fastapi import APIRouter, Depends, HTTPException, Form, Body, Request
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.db.base import get_db
import datetime
from app.schemas.job import JobBase, JobStatusModel, JobCreate, JobRequestModel

from app.core.job_manager import job_manager


router = APIRouter()

@router.get("/status/{job_id}")
def get_job_status(job: JobBase = Form(...), current_user: dict = Depends(get_current_user), response_model = JobStatusModel):
    # Return job info for job_id
    j_stat = job_manager.get_job_status(job.id)

    return {
        "job_id": job.id,
        "job_status": j_stat["status"]
    }

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