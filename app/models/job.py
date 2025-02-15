from sqlalchemy import Column, Integer, String, DateTime, func, Enum, Double
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class JobStatus(enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"
    paused = "paused"

class JobType(enum.Enum):
    minimize = "minimize"
    generate_kraus = "generate_kraus"
    generate_vector = "generate_vector"

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(Enum(JobType), nullable=False)  # e.g., "minimize", "generate_kraus"
    status = Column(Enum(JobStatus), default=JobStatus.pending, nullable=False)
    input_data = Column(JSONB, nullable=True)  # Correct column type
    kraus_operator = Column(String) # Id associated to kraus operators, be it input or output of the job
    vector = Column(String) # Id associated to the vector, be it input or output of the job
    entropy = Column(Double, nullable=False, default=-1.0)  # Default -1
    num_iterations = Column(Integer, default=0)
    time_created = Column(DateTime, server_default=func.now())
    time_started = Column(DateTime)
    time_finished = Column(DateTime)
    last_update = Column(DateTime)
    worker_id = Column(String)
    channel_id = Column(Integer, nullable=True)
    priority = Column(Integer, default=1)

