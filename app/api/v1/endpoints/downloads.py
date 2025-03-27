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
async def upload_file(token: str, 
                      file: UploadFile = FileField(...), 
                      job_id : str = Form(...),
                      file_type : str = Form(...), 
                      # The next part handles chunk uploads
                      session_id: str = Form(...), # A client-generated session ID. Used to verify that all chunks come from the same upload request.
                      chunk_index: int = Form(...), # The index of the current chunk, starts at 1
                      total_chunks: int = Form(...), # The total number of chunks
                      # Dependencies
                      db: Session = Depends(get_db),
                      current_user: dict = Depends(get_current_user)):
    """
    Securely upload a file in chunks using a one-time token.


    Current problems with this implementation: no checks for the chunks arriving in the correct order. No checks for missing chunks. No file integrity checks. No checks that uploads all come from the same upload request (say the client has crashed). 
    TODO: implement saving files to .tmp with chunk info and some unique identifier for the session. Then when all chunks are received, combine them into a single file and revoke the token. Q: should trust the client when it says "total 9 chunks" or how do we check the total number of chunks?


    """

    print("Upload request received", flush=True)
    print("Checking token...", flush=True)
    
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
    print("Job found and user authorized", flush=True)

    # Step 3: Check if token_info contains a file path and a session ID.
    file_path = token_info.get("file_path", None)
    token_session_id = token_info.get("session_id", None)
    # No path specified.
    if not file_path:    
        unique_filename = f"{uuid.uuid4()}.dat"
        unique_id = str(uuid.uuid4())[:8]
        file_path = os.path.join(cfg.save_path, unique_filename)
        token_info["file_path"] = file_path
        redis_client.setex(token, timedelta(seconds=cfg.upload_link_ttl), json.dumps(token_info))
    print("File path: ", file_path, flush=True)
    # No session ID specified.
    if not token_session_id:
        token_info["session_id"] = session_id
        redis_client.setex(token, timedelta(seconds=cfg.upload_link_ttl), json.dumps(token_info))

    # Handle session ID mismatch
    if token_session_id != session_id:
        # Invalidate token
        redis_client.delete(token)
        print("Session ID mismatch", flush=True)
        print(f"Invalidated token {token}", flush=True)
        raise HTTPException(status_code=403, detail="Session ID mismatch")


    # Step 4: Get a tmp file path
    os.makedirs(cfg.tmp_path, exist_ok=True)
    tmp_file_path = os.path.join(cfg.tmp_path, f"{session_id}_{chunk_index}.tmp")
    print(f"Temporary file path: {tmp_file_path}", flush=True)

    # Step 5: Check that the file doesn't already exist, else invalidate and return an error
    if os.path.isfile(tmp_file_path):
        # Invalidate token
        redis_client.delete(token)
        print("File already exists", flush=True)
        print(f"Invalidated token {token}", flush=True)
        raise HTTPException(status_code=403, detail="File already exists. Upload session aborted.")

    # Step 6: Write the chunk to the tmp file
    try:
        async with aiofiles.open(tmp_file_path, "wb") as tmp_file:  # Open in write mode
            print(f"Opened file {tmp_file_path} in write mode", flush=True)
            
            # Write the received chunk
            chunk_data = await file.read()  # Read the current chunk of data
            await tmp_file.write(chunk_data)  # Append the chunk to the file
            print(f"Chunk {chunk_index}/{total_chunks} written to {file_path}", flush=True)

    except Exception as e:
        print(f"Error while writing the file: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    # Step 7: Check that all chunks have been received
    # look in the tmp folder for all chunks
    tmp_files = os.listdir(cfg.tmp_path)
    chunks = []
    for file in tmp_files:
        if session_id in file:
            chunks.append(int(file.split("_")[-1].split(".")[0]))
    chunks.sort()
    print(f"Chunks received: {chunks}", flush=True)
    # If all chunks have been received, combine them into a single file
    if chunks == list(range(1, total_chunks + 1)):
        print("All chunks received, combining...", flush=True)
        try:
            os.makedirs(cfg.save_path, exist_ok=True)
            with open(file_path, "wb") as final_file:
                for chunk in chunks:
                    with open(os.path.join(cfg.tmp_path, f"{session_id}_{chunk}.tmp"), "rb") as tmp_file:
                        final_file.write(tmp_file.read())
            print("Chunks combined into a single file", flush=True)

            # Delete the tmp files
            print("Deleting temporary files...", flush=True)
            for chunk in chunks:
                os.remove(os.path.join(cfg.tmp_path, f"{session_id}_{chunk}.tmp"))

            # Store file metadata in the database
            new_file = File(id=unique_id, type=file_type, full_path=file_path)
            db.add(new_file)
            db.commit()
            db.refresh(new_file)
            print("DB entry created for file", flush=True)

            # Step 6: Invalidate token after successful upload
            redis_client.delete(token)
            print("Token invalidated", flush=True)

            # Step 7: Update the job entry with the file ID
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
                print("Job entry committed to DB", flush=True)
            except Exception as e:
                db.rollback()  # Undo changes if commit fails
                raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")
            
            print("Upload successful", flush=True)
            return {"message": "Upload successful"}



            

        except Exception as e:
            print(f"Error while combining the chunks: {str(e)}", flush=True)
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    else:
        print("Waiting for other chunks", flush=True)
        return {"message": "Chunk received, waiting for other chunks"}
