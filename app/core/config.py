# dataclass for configuration
from dataclasses import dataclass

@dataclass
class JobManagerConfig:
    job_paused_ttl: int = 60 * 60 * 24  # 1 day
    job_running_ttl: int = 60 * 60 * 24 * 30  # 30 days
    job_ping_ttl: int = 60 * 5  # 5 minutes, how often workers need to ping the server

@dataclass
class FileHandlingConfig:
    download_link_ttl: int = 60 * 5  # 5 minutes
    upload_link_ttl: int = 60 * 5  # 5 minutes

    chunk_size: int = 1024 * 1024  # 1 MB

    save_path = "/data"  # Where files are stored
    tmp_path = "/tmp"  # Where files are temporarily stored

@dataclass
class ChannelHandlingConfig:
    channel_number_of_runs: int = 100
    channel_max_jobs: int = 5
    update_interval: int = 5  # 5 seconds

