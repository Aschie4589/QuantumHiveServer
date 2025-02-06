from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserResponse # Import the UserCreate and UserResponse Pydantic models (i.e. the schemas for the request and response bodies)
from app.models.user import User # Import the User ORM model (i.e. the database model for the User table)
from app.core.security import hash_password
from app.db.base import get_db

router = APIRouter()

@router.post("/signup", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    db_mail = db.query(User).filter(User.email == user.email).first()
    if db_user or db_mail:
        raise HTTPException(status_code=400, detail="Username or mail already exists")
    new_user = User(username=user.username, password_hash=hash_password(user.password), email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/user/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
