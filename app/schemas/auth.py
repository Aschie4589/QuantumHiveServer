# Here we define the Pydantic models for the User and Token schemas. 
# Pydantic is a data validation library that uses Python type annotations to validate data. 
# Pydantic models are used to define the structure of the data that will be sent and received by the API. 

from pydantic import BaseModel

class TokenBase(BaseModel):
    #"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    access_token: str
    refresh_token: str
    token_type: str

