from sqlalchemy.orm import Session
from app.models.job import Job, JobStatus, JobType
import redis
import datetime
from app.core.config import JobManagerConfig
from app.db.base import SessionFactory
from app.core.redis import redis_client
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError, DataError
import time


class JobManager:
    def __init__(self, redis_client: redis.Redis, config: JobManagerConfig = JobManagerConfig()):
        self.db = None # Database session, this is set using the _get_session method
        # In-memory storage (fast access, queue)
        self.redis = redis_client
        # Sync the jobs in the database with the Redis queue
        self.sync_jobs()
        # Configuration
        self.config = config
    
    # JobManager does not have direct access to the get_db method, instead it has its own session management method.

    ############################
    # Session management methods
    ############################


    def _get_session(self):
        """Get a new database session. Handle Exceptions"""
        try:
            session = SessionFactory()
            return session
        except Exception as e:
            return None
        
    def ensure_session(func):
        """Decorator to handle session rollback, and logging."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.db = self._get_session() # Get a new session
            try:
                result = func(self, *args, **kwargs)  # Call the original method
                # no commit here, only commit in the called method
                return result
            except IntegrityError as e:
                # Handle IntegrityError (e.g., foreign key violations, unique constraint violations)
                print(f"Integrity error in method {func.__name__}: {str(e)}")
                self.db.rollback()
                raise
            except OperationalError as e:
                # Handle OperationalError (e.g., connection issues, timeouts)
                print(f"Operational error in method {func.__name__}: {str(e)}")
                self.db.rollback()
                raise
            except DataError as e:
                # Handle DataError (e.g., invalid data types, out-of-range values)
                print(f"Data error in method {func.__name__}: {str(e)}")
                self.db.rollback()
                raise
            except SQLAlchemyError as e:
                # Catch any other SQLAlchemy-related errors
                print(f"SQLAlchemy error in method {func.__name__}: {str(e)}")
                self.db.rollback()
                raise
            except Exception as e:
                # Catch any other unexpected errors
                print(f"Unexpected error in method {func.__name__}: {str(e)}")
                self.db.rollback()
                raise
            finally:
                if self.db:
                    self.db.close()  # Always close the session after use
                    self.db = None
        return wrapper



    ############################
    # Job management logic
    ############################

    def manage_jobs(self):
        '''
        Manage the jobs in the database. This function is called periodically to check the status of jobs and workers.
        It performs the following tasks:
        - Mark jobs of workers that have not pinged the server in a while as available
        - Restart paused jobs that have exceeded the pause TTL
        - Restart running jobs that have exceeded the running TTL
        - Restart canceled jobs
        '''
        print("Now managing jobs...!")
        # get a new session (this has to be separate from db, since that is used in the individual methods)
        session = self._get_session()
        if not session:
            print("Failed to get a session.")
            return
        running_jobs = session.query(Job).filter(Job.status == JobStatus.running).all()
        paused_jobs = session.query(Job).filter(Job.status == JobStatus.paused).all()
        canceled_jobs = session.query(Job).filter(Job.status == JobStatus.canceled).all()
        # Mark jobs of workers that have not pinged the server in a while as available
        for job in running_jobs:
            if job.last_update + datetime.timedelta(seconds=self.config.job_ping_ttl) < datetime.datetime.now():
                print(f"Worker {job.worker_id} has not pinged the server in a while. Marking job as available.")
                self.restart_job(job.id)
        # Restart paused jobs that have exceeded the pause TTL
        # TODO: notify the user?
        for job in paused_jobs:
            if job.time_started + datetime.timedelta(seconds=self.config.job_paused_ttl) < datetime.datetime.now():
                print(f"Job {job.id} has been paused for too long. Restarting.")
                self.restart_job(job.id)
        # Restart running jobs that have exceeded the running TTL
        # TODO: notify the user?
        for job in running_jobs:
            if job.time_started + datetime.timedelta(seconds=self.config.job_running_ttl) < datetime.datetime.now():
                print(f"Job {job.id} has been running for too long. Restarting.")
                self.restart_job(job.id)
        # Reschedule cancelled jobs. Simply spawn a new job with the same information.
        for job in canceled_jobs:
            print(f"Job {job.id} was canceled. Restarting.")
            self.create_job(job.job_type, job.input_data, job.kraus_operator, job.vector, job.channel_id)

#            self.restart_job(job.id)
        print("Job management complete.")
        # Close the session
        session.close()


    def sync_jobs(self):
        '''
        Sync the jobs in the database with the Redis queue. This can be expensive if there are many jobs.
        The goal is to ensure that all pending jobs are in the Redis queue and that the queue does not contain jobs that are no longer pending.
        '''
        print("Syncing jobs...")
        session = self._get_session()
        # Make sure all pending jobs are in the Redis queue
        pending_jobs = session.query(Job).filter(Job.status == JobStatus.pending).all()
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
            job = session.query(Job).filter(Job.id == job_id).first()
            if job.status != JobStatus.pending:
                self.redis.lrem("job_queue", 0, job_id)
                continue
        else:
            print("No non-pending jobs to remove from the Redis queue.")
        session.close()
        print("Job sync complete.")

    #############################
    # Job creation and assignment
    #############################

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

        # Add job to the database
        session = self._get_session()
        session.add(new_job)
        session.commit()
        session.refresh(new_job)
        session.close()

        # Add job to Redis queue
        self.redis.rpush("job_queue", new_job.id)
        return new_job
    

    @ensure_session         
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
            session = self._get_session()
            job = session.query(Job).filter(Job.id == job_id).first()

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
            session.commit()
            session.close()
            print("Job assigned to worker:", worker_id)
            return job

    ############################
    #          Getters
    ############################
    @ensure_session
    def get_assigned_worker(self, job_id: int):
        """Get the worker assigned to a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"id": job.worker_id}

    @ensure_session
    def get_job_status(self, job_id: int):
        """Retrieve job status by ID."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"id": job.id, "status": job.status.value}

    @ensure_session
    def get_job_type(self, job_id: int):
        """Retrieve job type by ID."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"job_type": job.job_type}

    @ensure_session
    def get_kraus(self, job_id: int):
        """Retrieve the Kraus operator for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"kraus_operator": job.kraus_operator}

    @ensure_session
    def get_vector(self, job_id: int):
        """Retrieve the vector for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"vector": job.vector} 

    @ensure_session
    def get_input_data(self, job_id: int):
        """Retrieve the vector for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"input_data": job.input_data} 

    @ensure_session
    def get_entropy(self, job_id: int):
        """Retrieve the entropy for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"entropy": job.entropy} 

    @ensure_session
    def get_channel(self, job_id: int):
        """Retrieve the channel for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return {"channel_id": job.channel_id} 

    ############################
    #         Setters
    ############################

    @ensure_session
    def update_job_status(self, job_id: int, status: JobStatus):
        """Update the status of a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.status = status
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

    @ensure_session
    def update_kraus(self, job_id: int, kraus: str):
        """Update the Kraus operator for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.kraus_operator = kraus
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

    @ensure_session
    def update_vector(self, job_id: int, vector: str):
        """Update the vector for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        job.vector = vector
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

    @ensure_session
    def update_iterations(self, job_id: int, num_iterations: int):
        """Update the number of iterations for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.num_iterations = num_iterations
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job
    
    @ensure_session
    def update_entropy(self, job_id: int, entropy: float):
        """Update the entropy for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.entropy = entropy
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

    @ensure_session
    def update_channel(self, job_id: int, channel_id: int):
        """Update the entropy for a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.channel_id = channel_id
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

    @ensure_session
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

    @ensure_session
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

    @ensure_session
    def ping_worker(self, worker_id: str, job_id: int):
        """Update the last ping time for a worker."""
        job = self.db.query(Job).filter(Job.worker_id == worker_id).filter(Job.status == JobStatus.running).filter(Job.id == job_id).first()
        if not job:
            return None
        print("Pinging worker:", worker_id)
        print("Job ID:", job.id)
        job.last_update = datetime.datetime.now()
        self.db.commit()
        return job

# ------------------------------
# Job Manager logic
# ------------------------------

job_manager = JobManager(redis_client)


