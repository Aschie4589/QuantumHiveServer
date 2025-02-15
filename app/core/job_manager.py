from sqlalchemy.orm import Session
from app.models.job import Job, JobStatus, JobType
import redis
import datetime
from app.core.config import JobManagerConfig
from app.db.base import SessionLocal
from app.core.redis import redis_client

class JobManager:
    def __init__(self, db: Session, redis_client: redis.Redis, config: JobManagerConfig = JobManagerConfig()):
        # Persistent storage
        self.db = db
        # In-memory storage (fast access, queue)
        self.redis = redis_client
        # Sync the jobs in the database with the Redis queue
        self.sync_jobs()
        # Configuration
        self.config = config

    def manage_jobs(self):
        '''
        Manage the jobs in the database. This function is called periodically to check the status of jobs and workers.
        It performs the following tasks:
        - Mark jobs of workers that have not pinged the server in a while as available
        - Restart paused jobs that have exceeded the pause TTL
        - Restart running jobs that have exceeded the running TTL
        '''
        running_jobs = self.db.query(Job).filter(Job.status == JobStatus.running).all()
        paused_jobs = self.db.query(Job).filter(Job.status == JobStatus.paused).all()
        # Mark jobs of workers that have not pinged the server in a while as available
        for job in running_jobs:
            if job.last_update + datetime.timedelta(seconds=self.config.job_ping_ttl) < datetime.datetime.now():
                job.status = JobStatus.pending
                job.last_update = datetime.datetime.now()
                self.db.commit()
        # Restart paused jobs that have exceeded the pause TTL
        # TODO: notify the user?
        for job in paused_jobs:
            if job.time_started + datetime.timedelta(seconds=self.config.job_paused_ttl) < datetime.datetime.now():
                self.restart_job(job.id)
        # Restart running jobs that have exceeded the running TTL
        # TODO: notify the user?
        for job in running_jobs:
            if job.time_started + datetime.timedelta(seconds=self.config.job_running_ttl) < datetime.datetime.now():
                self.restart_job(job.id)

    def sync_jobs(self):
        '''
        Sync the jobs in the database with the Redis queue. This can be expensive if there are many jobs.
        The goal is to ensure that all pending jobs are in the Redis queue and that the queue does not contain jobs that are no longer pending.
        '''
        # Make sure all pending jobs are in the Redis queue
        pending_jobs = self.db.query(Job).filter(Job.status == JobStatus.pending).all()
        # Add pending jobs to the Redis queue if they are not already there
        for job in pending_jobs:
            if not self.redis.lrange("job_queue", 0, -1):
                self.redis.rpush("job_queue", job.id)
                continue
            elif job.id not in self.redis.lrange("job_queue", 0, -1):
                self.redis.rpush("job_queue", job.id)
                continue
        else:
            print("No pending jobs to add to the Redis queue.")
        # Next purge the Redis queue of jobs that are no longer pending
        job_queue = self.redis.lrange("job_queue", 0, -1)
        for job_id in job_queue:
            #cast to int
            job_id = int(job_id)
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job.status != JobStatus.pending:
                self.redis.lrem("job_queue", 0, job_id)
                continue
        else:
            print("No non-pending jobs to remove from the Redis queue.")
                            
    def create_job(self, job_type: JobType, input_data: dict, kraus_operators: str = None, vector: str = None, channel_id: int = -1):
        """Create a new job and queue it."""
        if job_type == JobType.minimize:
            # debug. print all passed things
            print("Passed input data:", input_data)
            print("Passed kraus operators:", kraus_operators)
            print("Passed vector:", vector)

            if vector and kraus_operators:
                new_job = Job(job_type=JobType.minimize, status=JobStatus.pending, input_data=input_data, kraus_operator=kraus_operators, vector=vector, channel_id=channel_id)
            else:
                print("Missing required parameters for minimize job.")
                return None

        elif job_type == JobType.generate_kraus:
            new_job = Job(job_type=JobType.generate_kraus, status=JobStatus.pending, input_data=input_data, channel_id=channel_id)

        elif job_type == JobType.generate_vector:
            new_job = Job(job_type=JobType.generate_vector, status=JobStatus.pending, input_data=input_data, channel_id=channel_id)
        else:
            print("Invalid job type.")
            return None
        new_job.last_update = datetime.datetime.now()
        new_job.time_created = datetime.datetime.now()
        self.db.add(new_job)
        self.db.commit()
        self.db.refresh(new_job)

        # Add job to Redis queue
        self.redis.rpush("job_queue", new_job.id)
        return new_job

    def assign_job_to_worker(self, worker_id: str):
            """Assign a job to an available worker."""
            print("Assigning job to worker:", worker_id)
            # Get a job from the Redis queue
            job_id = self.redis.lpop("job_queue")
            if not job_id:
                print("No jobs available.")
                return None  # No jobs available
            job_id = int(job_id)
            print("Job ID:", job_id)

            # Lock the job and mark it as 'running' in the database
            job = self.db.query(Job).filter(Job.id == job_id).first()

            if not job:
                # Database inconsistency: job in the queue but not in the database
                # Log this
                print(f"Job {job_id} not found in the database, but present in Redis.")
                return self.assign_job_to_worker(worker_id)  # Retry

            if job.status != JobStatus.pending:
                # Job is not available for assignment (already running, completed, etc.)
                print("Possible database inconsistency: Job is not pending.")
                print("Job status:", job.status)
                print("Will refresh the Redis queue.")
                self.sync_jobs()
                return self.assign_job_to_worker(worker_id)  # Retry

            # Update the job status to "running" and assign the worker
            job.status = JobStatus.running
            job.worker_id = worker_id  # Assign the job to the worker
            job.time_started = datetime.datetime.now()
            job.last_update = datetime.datetime.now()
            self.db.commit()
            print("Job assigned to worker:", worker_id)
            return job

    def get_assigned_worker(self, job_id: int):
        """Get the worker assigned to a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"id": job.worker_id}

    def get_job_status(self, job_id: int):
        """Retrieve job status by ID."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"id": job.id, "status": job.status.value}

    def get_job_type(self, job_id: int):
        """Retrieve job type by ID."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"job_type": job.job_type}

    def get_kraus(self, job_id: int):
        """Retrieve the Kraus operator for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"kraus_operator": job.kraus_operator}

    def get_vector(self, job_id: int):
        """Retrieve the vector for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"vector": job.vector} 

    def get_input_data(self, job_id: int):
        """Retrieve the vector for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"input_data": job.input_data} 

    def get_entropy(self, job_id: int):
        """Retrieve the entropy for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"entropy": job.entropy} 
    
    def get_channel(self, job_id: int):
        """Retrieve the channel for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"channel_id": job.channel_id} 

    def update_job_status(self, job_id: int, status: JobStatus):
        """Update the status of a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.status = status
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

    def update_kraus(self, job_id: int, kraus: str):
        """Update the Kraus operator for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.kraus_operator = kraus
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

    def update_vector(self, job_id: int, vector: str):
        """Update the vector for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        job.vector = vector
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

    def update_iterations(self, job_id: int, num_iterations: int):
        """Update the number of iterations for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.num_iterations = num_iterations
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job
    
    def update_entropy(self, job_id: int, entropy: float):
        """Update the entropy for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.entropy = entropy
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

    def update_channel(self, job_id: int, channel_id: int):
        """Update the entropy for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.channel_id = channel_id
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job


    def complete_job(self, job_id: int):
        """Mark a job as completed. Add it to redis for the channel manager to process."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.status = JobStatus.completed
        job.time_finished = datetime.datetime.now()
        job.last_update = datetime.datetime.now()
        self.db.commit()
        self.redis.rpush("to_process", job.id)
        return job  

    def restart_job(self, job_id: int):
        """Restart a job that was previously paused."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        job.status = JobStatus.pending
        job.time_started = None
        job.time_finished = None
        job.last_update = datetime.datetime.now()
        self.db.commit()
        self.redis.rpush("job_queue", job.id)
        return job

    def ping_worker(self, worker_id: str):
        """Update the last ping time for a worker."""
        jobs = self.db.query(Job).filter(Job.worker_id == worker_id).filter(Job.status == JobStatus.running).all()
        if not jobs:
            return None
        for job in jobs:
            print("Pinging worker:", worker_id)
            print("Job ID:", job.id)
            job.last_update = datetime.datetime.now()
        self.db.commit()
        return jobs
# ------------------------------
# Job Manager logic
# ------------------------------

job_manager = JobManager(SessionLocal(), redis_client)


