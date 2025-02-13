import uuid
from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, Body
from fastapi import File as FileField
from starlette.responses import FileResponse
from app.core.security import get_current_user
from app.db.base import get_db
from app.models.file import File
from app.models.job import Job
from app.models.file import FileTypeEnum
from app.schemas.file import FileRequestBase, FileResponseBase, FileUploadRequestBase, FileUploadResponseBase
from app.core.redis import redis_client
import json
import os
from app.core.config import FileHandlingConfig
import shutil
from app.core.job_manager import job_manager

router = APIRouter()
cfg = FileHandlingConfig()
import json



######################
# File Download API #
######################

def generate_download_link(file_id: str, current_user: dict, db: Session):
    """
    Generate a one-time-use download link for a file, associated with the requesting user.
    """
    # Step 1: Validate the file exists
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Step 2: Generate a unique token
    token = str(uuid.uuid4())

    # Step 3: Store token in Redis with file path + user ID (expires in 5 minutes)
    token_data = json.dumps({"file_path": file.full_path, "user_id": current_user["sub"]})
    redis_client.setex(token, timedelta(seconds=cfg.download_link_ttl), token_data)

    # Step 4: Return the secure download link
    return {"download_url": f"files/download/{token}"}

@router.get("/download/{token}")
def download_file(token: str, current_user: dict = Depends(get_current_user)):
    """
    Serve a file if the provided token is valid and belongs to the requesting user.
    """
    # Step 1: Retrieve token data from Redis
    token_data = redis_client.get(token)
    if not token_data:
        raise HTTPException(status_code=403, detail="Invalid or expired token")

    # Step 2: Parse the token data (file path + user ID)
    token_info = json.loads(token_data)
    file_path = token_info["file_path"]
    user_id = token_info["user_id"]

    # Step 3: Ensure the requesting user is the same who requested the link
    if user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    # Step 4: Invalidate token (one-time use)
    redis_client.delete(token)

    # Step 5: Return the file as a response. TODO: Check the file path is right?
    return FileResponse(file_path, filename=file_path.split("/")[-1], media_type="application/octet-stream")

@router.get("/request-download")
def request_download(file_req: FileRequestBase = Form(...), db: Session = Depends(get_db),current_user: dict = Depends(get_current_user), response_model = FileResponseBase):
    """
    Request a secure download link for a file.
    Validates that the file exists and generates a one-time token for the requesting user.
    """
    # Step 1: Check if the file exists
    file = db.query(File).filter(File.id == file_req.id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    # TODO: implement a check to see if the user should be able to access this file!

    # Step 2: Generate a one-time download token (linked to the user)
    return generate_download_link(file_req.id, current_user, db)

######################
#   File Upload API  #
######################

def generate_upload_link(current_user: dict):
    """
    Generate a one-time secure upload link after a job is completed.
    """
    # Step 2: Generate a unique upload token
    token = str(uuid.uuid4())

    # Step 3: Store token in Redis with job info
    token_data = json.dumps({
        "user_id": current_user["sub"],
    })
    redis_client.setex(token, timedelta(seconds=cfg.upload_link_ttl), token_data)

    # Step 4: Return the secure upload link
    return {"upload_url": f"files/upload/{token}"}

@router.get("/request-upload")
def request_upload(current_user: dict = Depends(get_current_user), response_model = FileUploadResponseBase):
    """
    Request an upload link after a job is finished.
    """
    return generate_upload_link(current_user)



@router.post("/upload/{token}")
async def upload_file(token: str, file: UploadFile = FileField(...), job_id : str = Form(...),file_type : str = Form(...),db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    """
    Securely upload a file using a one-time token. TODO: validate the file!!!
    """
    # Step 1: Retrieve and validate the token from Redis
    token_data = redis_client.get(token)
    if not token_data:
        raise HTTPException(status_code=403, detail="Invalid or expired upload token")

    token_info = json.loads(token_data)
    user_id = token_info["user_id"]


    # Step 2: Ensure the requesting user matches the token user
    if user_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    # Step 3: Save the file to the server. Extension is just .dat
    unique_filename = f"{uuid.uuid4()}.dat"
    unique_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(cfg.save_path, unique_filename)
    try:
        job_manager.get_job_status
        jb = db.query(Job).filter(Job.id == job_id).first()
        if not jb:
            raise HTTPException(status_code=404, detail="Job not found")
        # ensure path exists
        os.makedirs(cfg.save_path, exist_ok=True)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Step 4: Store file metadata in the database
        new_file = File(id=unique_id, type=file_type, full_path=file_path)
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        # Step 5: Invalidate token (only after successful upload)
        redis_client.delete(token)

        # Step 6: update the job entry corresponding to the job_id with the file id
        # pruint debug
        print("job_id",job_id)
        print("file_type",file_type)
        print("unique_id",unique_id)
        
        try:
            file_type_enum = FileTypeEnum(file_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file_type}")

        if file_type_enum == FileTypeEnum.kraus:
            print("Detected kraus")
            jb.kraus_operator = unique_id
        elif file_type_enum == FileTypeEnum.vector:
            print("Detected vector")
            jb.vector = unique_id
        try:
            db.commit()
            db.refresh(jb)
        except Exception as e:
            db.rollback()  # Undo changes if commit fails
            raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")
        return {"message": "Upload successful"}

    except Exception as e:
        # Handle failure by logging (token remains valid for retry)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

