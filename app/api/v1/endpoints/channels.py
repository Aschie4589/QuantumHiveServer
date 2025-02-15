from fastapi import APIRouter, Depends, HTTPException, Form, Body, Query
# Schemas
from app.schemas.channel import ChannelCreateHaar, ChannelResponseBase
from typing import List
# Models
from app.models.channel import Channel
from app.models.job import JobStatus
# Core
from app.core.job_manager import job_manager
from app.core.channel_manager import channel_manager
from app.core.security import get_current_user

router = APIRouter()

@router.post("/create")
def create_channel(cmd: ChannelCreateHaar = Form(...), current_user: dict = Depends(get_current_user)):
    # TODO: only admin can create channels
    # TODO: use method to specify the channel type
    # for now parameter is unused    
    # create the channel
    c = channel_manager.create_channel(cmd.input_dimension, cmd.output_dimension, cmd.num_kraus)
    if not c:
        raise HTTPException(status_code=400, detail="Channel creation failed")
    else:
        return {"result": "success"}
    
@router.get("/list", response_model = List[ChannelResponseBase])
def list_channels(current_user: dict = Depends(get_current_user)):
    # TODO (later): only admin can list channels
    # list all channels
    c = channel_manager.get_channels()
    if not c:
        raise HTTPException(status_code=404, detail="No channels found")
    else:
        return c
    
# debugging endpoint "/update"
@router.post("/update")
async def update_channel(current_user: dict = Depends(get_current_user)):
    # async update the channel (so wait until it is done)
    try:
        await channel_manager.update()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    