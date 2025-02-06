# dataclass for configuration
from dataclasses import dataclass

@dataclass
class JobManagerConfig:
    job_paused_ttl: int = 60 * 60 * 24  # 1 day
    job_running_ttl: int = 60 * 60 * 24 * 30  # 30 days
    job_ping_ttl: int = 60 * 5  # 5 minutes, how often workers need to ping the server
