# Here we define the Pydantic models for the User and Token schemas. 
# Pydantic is a data validation library that uses Python type annotations to validate data. 
# Pydantic models are used to define the structure of the data that will be sent and received by the API. 

from pydantic import BaseModel

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    email: str
    password: str

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    class Config: # This is a Pydantic model configuration class. It is used to configure the behavior of the Pydantic model.
        from_attributes = True # This tells Pydantic to generate the model fields from the class attributes.