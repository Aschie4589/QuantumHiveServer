from sqlalchemy import Column, String, Integer, Double, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

# Define an Enum class for status
class ChannelStatusEnum(str, enum.Enum):
    created = "created"
    generating = "generating"
    minimizing = "minimizing"
    paused = "paused"
    completed = "completed"

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kraus_id = Column(String(8), nullable=True, default=None)  # Starts blank
    best_moe = Column(Double, nullable=False, default=-1.0)  # Default -1
    best_entropy_vector_id = Column(String(8), nullable=True, default=None)  # Starts blank
    minimization_attempts = Column(Integer, nullable=False, default=100)  # Defaults to 100
    runs_spawned = Column(Integer, nullable=False, default=0)
    runs_completed = Column(Integer, nullable=False, default=0)
    input_dimension = Column(Integer, nullable=False)
    output_dimension = Column(Integer, nullable=False)
    num_kraus = Column(Integer, nullable=False)
    status = Column(Enum(ChannelStatusEnum), nullable=False, default=ChannelStatusEnum.created)  # Use ENUM

    def __repr__(self):
        return f"<Channel(id={self.id}, status={self.status})>"