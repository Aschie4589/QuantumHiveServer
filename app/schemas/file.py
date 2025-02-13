# Here we define the Pydantic models for the User and Token schemas. 
# Pydantic is a data validation library that uses Python type annotations to validate data. 
# Pydantic models are used to define the structure of the data that will be sent and received by the API. 

from pydantic import BaseModel

class FileRequestBase(BaseModel):
    id : str

class FileResponseBase(BaseModel):
    download_url: str

class FileUploadRequestBase(BaseModel):
    job_id: int
    file_type: str # "kraus" or "vector"

class FileUploadResponseBase(BaseModel):
    upload_url: str