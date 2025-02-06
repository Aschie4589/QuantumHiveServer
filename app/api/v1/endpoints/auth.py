from fastapi import APIRouter, Depends, HTTPException, Form, Header, Request
from sqlalchemy.orm import Session
from app.schemas.user import UserLogin
from app.schemas.auth import TokenBase
from app.models.user import User # Import the User ORM model (i.e. the database model for the User table)
from app.core.security import verify_password, create_token, verify_token, is_token_revoked, revoke_token, get_current_user
from app.db.base import get_db
import datetime


router = APIRouter()


@router.post("/login")
def login(request: Request, user: UserLogin = Form(...), db: Session = Depends(get_db), response_model=TokenBase):
    # Retrieve the username and hashed password from the database
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)

    print("Login attempt with user:", user.username)
    # Print request time and address
    print("Login client address:", request.client.host)
    print("Login client address (X-Forwarded-For):", client_ip)

    db_user = db.query(User).filter(User.username == user.username).first()
    # Validate the username and password (this can be improved) TODO: improve this!
    if user.username == db_user.username and verify_password(user.password, db_user.password_hash):
        # Create tokens and send them to user.
        access_token = create_token(data={"sub": user.username, "type": "access"})
        ## TODO: this is hardcoded!!! Fix this.
        refresh_token = create_token(data={"sub": user.username, "type": "refresh"}, expires_delta=datetime.timedelta(days=30))
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/refresh")
# refresh the access token. Refresh is included as Header in the request.
def refresh_token(refresh: str = Header(...), response_model=TokenBase):
    # Verify the refresh token
    payload = verify_token(refresh)
    print("Payload:", payload)
    if payload["type"] != "refresh":
        raise HTTPException(status_code=400, detail="Invalid token type")
    # Check if the token is revoked
    if is_token_revoked(refresh):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    # Next revoke the refresh token
    revoke_token(refresh)
    print("Have revoked token, now creating new token (refresh)")
    # Create a new access token and return it. Rotate the refresh token. TODO: this is hardcoded!!! Fix this.
    # Also, there is a problem if a token is revoked too fast after creation. The new token will be revoked too (it is the same token).
    access_token = create_token(data={"sub": payload["sub"], "type": "access"})
    refresh_token = create_token(data={"sub": payload["sub"], "type": "refresh"}, expires_delta=datetime.timedelta(days=30))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.get("/status")
def status(current_user: dict = Depends(get_current_user)):
    # Dummy status info. Add user.
    return {
        "status": "Server is running",
        "user": current_user["sub"]
    }
