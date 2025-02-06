# This is a sqlalchemy ORM model. It represents the user table in the database.
# As such, it has a username and a hashed_password field.

from sqlalchemy import Column, Integer, String, TIMESTAMP, Text
from app.db.base import Base
from datetime import datetime, timezone

# Define the User model to contain the user information
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(50), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), default='user', nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)