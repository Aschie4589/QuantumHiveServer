from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Enum
from sqlalchemy.orm import relationship
from db.base import Base
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

'''
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    job_type TEXT NOT NULL CHECK (job_type IN ('minimize', 'generate_kraus', 'generate_vector')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'paused')),
    input_data JSONB,  -- Store job parameters in structured format
    kraus_operator TEXT,  -- File path or reference
    vector TEXT,  -- Store initial or final vector (or reference)
    num_iterations INTEGER DEFAULT 0,  -- Track how many iterations were run
    time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    time_started TIMESTAMP,
    time_finished TIMESTAMP,
    last_update TIMESTAMP,
    worker_id TEXT,  -- Assigned worker (nullable initially)
    priority INTEGER DEFAULT 1
'''
class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(Enum(JobType), nullable=False)  # e.g., "minimize", "generate_kraus"
    status = Column(Enum(JobStatus), default=JobStatus.pending, nullable=False)
    input_data = Column(String)  # JSON string
    kraus_operator = Column(String)
    vector = Column(String)
    num_iterations = Column(Integer, default=0)
    time_created = Column(DateTime, server_default=func.now())
    time_started = Column(DateTime)
    time_finished = Column(DateTime)
    last_update = Column(DateTime)
    worker_id = Column(String)
    priority = Column(Integer, default=1)

