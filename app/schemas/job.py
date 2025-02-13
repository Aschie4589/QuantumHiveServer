# Here we define the Pydantic models for the User and Token schemas. 
# Pydantic is a data validation library that uses Python type annotations to validate data. 
# Pydantic models are used to define the structure of the data that will be sent and received by the API. 

from pydantic import BaseModel
from typing import Dict, Any

class JobBase(BaseModel):
    job_id: int

class JobStatusModel(JobBase):
    job_status: str
    
class JobInfo(JobStatusModel):
    job_type: str

class JobCreate(BaseModel):
    job_type: str
    input_data: Dict[str, Any]  
    kraus_operator: str
    vector: str

class JobRequestModel(JobCreate):
    job_id: int    