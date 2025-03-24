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
from app.schemas.file import FileResponseBase, FileUploadRequestBase, FileUploadResponseBase, FileDownloadRequestBase
from app.core.redis import redis_client
import json
import os
from app.core.config import FileHandlingConfig
import aiofiles
from app.core.job_manager import job_manager
import datetime
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
    # Step 1: Check if the file exists
    # Skip since we already know the file exists (from the request_download endpoint)
    # Step 2: Generate a unique token
    token = str(uuid.uuid4())

    # Step 3: Store token in Redis with file path + user ID (expires in 5 minutes)
    token_data = json.dumps({"file_id": file_id, "user_id": current_user["sub"]})
    redis_client.setex(token, timedelta(seconds=cfg.download_link_ttl), token_data)

    # Step 4: Return the secure download link
    return {"download_url": f"/files/download/{token}"}

@router.post("/request-download")
def request_download(file_req: FileDownloadRequestBase = Body(...), db: Session = Depends(get_db),current_user: dict = Depends(get_current_user), response_model = FileResponseBase):
    """
    Request a secure download link for a file.
    Validates that the file exists and generates a one-time token for the requesting user.
    """
    # Step 1: Check if the file exists
    file = db.query(File).filter(File.id == file_req.file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    # TODO: implement a check to see if the user should be able to access this file!

    # Step 2: Generate a one-time download token (linked to the user)
    return generate_download_link(file_req.file_id, current_user, db)

@router.get("/download/{token}")
async def download_file(token: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Serve a file if the provided token is valid and belongs to the requesting user.
    """
    # Step 1: Retrieve token data from Redis
    token_data = redis_client.get(token)
    if not token_data:
        raise HTTPException(status_code=403, detail="Invalid or expired token")

    # Step 2: Parse the token data (file path + user ID)
    token_info = json.loads(token_data)
    file_id = token_info["file_id"]
    user_id = token_info["user_id"]

    # Step 3: Ensure the requesting user is the same who requested the link, and that the file exists
    if user_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    # get the file path
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    #check it points to a file
    if not os.path.isfile(file.full_path):
        raise HTTPException(status_code=404, detail="Invalid path. The file does not exist.")

    file_path = file.full_path
    # Step 4: Invalidate token (one-time use)
    redis_client.delete(token)

    # Step 5: Return the file as a response. TODO: Check the file path is right?
    return FileResponse(file_path, filename=file_path.split("/")[-1], media_type="application/octet-stream")



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
    return {"upload_url": f"/files/upload/{token}"}

@router.post("/request-upload")
def request_upload(current_user: dict = Depends(get_current_user), response_model = FileUploadResponseBase):
    """
    Request an upload link after a job is finished.
    """
    return generate_upload_link(current_user)


@router.post("/upload/{token}")
async def upload_file(token: str, file: UploadFile = FileField(...), job_id : str = Form(...),file_type : str = Form(...),db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    async with aiofiles.open(os.path.join(cfg.save_path, "prova123.dat"), "wb") as out_file:
        chunk_count = 0  # Track number of chunks
        while True:
            chunk = await file.read(cfg.chunk_size)
            if not chunk:
                print(f"End of file reached after {chunk_count} chunks")
                break
            chunk_count += 1
            print(f"Chunk {chunk_count}: {len(chunk)} bytes received", flush=True)  # Debugging output
            await out_file.write(chunk)
        
    

@router.post("/upload2/{token}")
async def upload2_file(token: str, file: UploadFile = FileField(...), job_id : str = Form(...),file_type : str = Form(...),db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
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

    jb = db.query(Job).filter(Job.id == job_id).first()
    if not jb:
        raise HTTPException(status_code=404, detail="Job not found")


    # Step 3: Save the file to the server. Extension is just .dat
    # Obtain filename
    unique_filename = f"{uuid.uuid4()}.dat"
    unique_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(cfg.save_path, unique_filename)

    try:
        # ensure path exists
        os.makedirs(cfg.save_path, exist_ok=True)
        # Save the file, read chunks
        async with aiofiles.open(file_path, "wb") as out_file:
            print("File received, saving to disk...", flush=True)
            chunk_count = 0  # Track number of chunks
            while True:
                chunk = await file.read(cfg.chunk_size)
                if not chunk:
                    print(f"End of file reached after {chunk_count} chunks", flush=True)
                    break
                chunk_count += 1
                print(f"Chunk {chunk_count}: {len(chunk)} bytes received", flush=True)  # Debugging output
                await out_file.write(chunk)

        # Step 4: Store file metadata in the database
        new_file = File(id=unique_id, type=file_type, full_path=file_path)
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        # Step 5: Invalidate token (only after successful upload)
        redis_client.delete(token)

        # Step 6: update the job entry corresponding to the job_id with the file id
        print("Committed to DB, updating job entry...", flush=True)        
        try:
            file_type_enum = FileTypeEnum(file_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file_type}")

        if file_type_enum == FileTypeEnum.kraus:
            jb.kraus_operator = unique_id
        elif file_type_enum == FileTypeEnum.vector:
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
        print("Error",str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

