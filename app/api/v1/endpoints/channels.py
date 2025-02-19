from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from app.db.base import get_db
# Schemas
from app.schemas.channel import ChannelCreateHaar, ChannelResponseBase, ChannelSetMinimizationAttempts
from typing import List
# Models
from app.models.user import User
# Core
from app.core.channel_manager import channel_manager
from app.core.security import get_current_user

router = APIRouter()

@router.post("/create")
def create_channel(cmd: ChannelCreateHaar = Form(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # TODO: only admin can create channels
    # TODO: use method to specify the channel type
    # for now parameter is unused    
    # create the channel
    
    # query the DB for current user and check if they are admin
    # if not, raise HTTPException(status_code=403, detail="Unauthorized user.")
    db_user = db.query(User).filter(User.username == current_user["sub"]).first()
    if not db_user or not db_user.role == "admin":
        raise HTTPException(status_code=403, detail="Unauthorized user.")

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
    
@router.post("/update-minimization-attempts")
def set_minimization_attempts(params: ChannelSetMinimizationAttempts = Form(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # set the number of minimization attempts. also check if the user is admin
    # query the DB for current user and check if they are admin
    # if not, raise HTTPException(status_code=403, detail="Unauthorized user.")
    db_user = db.query(User).filter(User.username == current_user["sub"]).first()
    if not db_user or not db_user.role == "admin":
        raise HTTPException(status_code=403, detail="Unauthorized user.")
    c = channel_manager.set_minimization_attempts(params.channel_id, params.attempts)
    if not c:
        raise HTTPException(status_code=400, detail="Setting minimization attempts failed")
    else:
        return {"result": "success"}

