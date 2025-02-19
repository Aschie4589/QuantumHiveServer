from pydantic import BaseModel

class ChannelCreateBase(BaseModel):
    input_dimension: int
    output_dimension: int
    num_kraus: int

class ChannelCreateHaar(ChannelCreateBase):
    method: str = "haar"

class ChannelResponseBase(BaseModel):
    id: int
    status: str

class ChannelSetMinimizationAttempts(BaseModel):
    channel_id: int
    attempts: int