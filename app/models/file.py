import uuid
from sqlalchemy import Column, String
from sqlalchemy.types import Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

def generate_unique_id():
    return str(uuid.uuid4())[:8]  # Generate a short, random unique ID

class FileTypeEnum(enum.Enum):
    kraus = "kraus"
    vector = "vector"

class File(Base):
    __tablename__ = "files"

    id = Column(String(8), primary_key=True, default=generate_unique_id, unique=True, index=True)
    type = Column(Enum(FileTypeEnum), nullable=False)  # Specifies the type of file, restricted to "kraus" or "vector"
    full_path = Column(String(255), nullable=False, unique=True)  # Stores the absolute path to the file, ensuring uniqueness

    def __repr__(self):
        return f"<File(id={self.id}, type={self.type}, full_path={self.full_path})>"