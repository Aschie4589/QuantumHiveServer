# Here we define the Pydantic models for the User and Token schemas. 
# Pydantic is a data validation library that uses Python type annotations to validate data. 
# Pydantic models are used to define the structure of the data that will be sent and received by the API. 

from pydantic import BaseModel, Field

class FileDownloadRequestBase(BaseModel):
    file_id : str


class FileResponseBase(BaseModel):
    download_url: str

class FileUploadRequestBase(BaseModel):
    job_id: int
    file_type: str # "kraus" or "vector"

class FileUploadRequestBase(BaseModel):
    job_id: str = Field(..., min_length=3, max_length=50)  # Validate length
    file_type: str = Field(..., pattern="^(kraus|vector)$")  # Validate allowed values

    class Config:
        # Ensures that data from form is handled properly
        # FastAPI will convert the form data into the appropriate Pydantic model
        orm_mode = True

class FileUploadResponseBase(BaseModel):
    upload_url: str