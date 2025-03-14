from sqlalchemy.orm import Session
import redis
from app.core.config import ChannelHandlingConfig
from app.db.base import SessionFactory
from functools import wraps
from sqlalchemy.exc import IntegrityError, OperationalError, DataError, SQLAlchemyError
from app.core.redis import redis_client
from app.core.job_manager import job_manager
from app.models.channel import Channel, ChannelStatusEnum
from app.models.job import JobType, JobStatus, Job
import asyncio


class ChannelManager:
    def __init__(self, redis_client: redis.Redis = redis_client, job_manager = job_manager, config: ChannelHandlingConfig = ChannelHandlingConfig()):
        self.db = None
        self.redis = redis_client
        self.config = config
        self.job_manager = job_manager

    ############################
    # Session management methods
    ############################


    def _get_session(self):
        """Get a new database session. Handle Exceptions"""
        try:
            session = SessionFactory()
            return session
        except Exception as e:
            print(f"Failed to get a session: {e}")
            return None
        
    def ensure_session(func):
        """Decorator to handle session commit, rollback, and logging."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.db = self._get_session()  # Ensure a session exists

            try:
                result = func(self, *args, **kwargs)  # Call the original method
                # cpmmit not needed, since we assume the method already takes care of this if necessary
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

    ######################
    #      Getters       #
    ######################

    @ensure_session
    def get_channels(self):
        """
        Get all channels. Connect to database and get all channels.
        Returns: List of channels if found, None otherwise.
        """
        channels = self.db.query(Channel).all()
        if not channels:
            return None
        return channels

    @ensure_session
    def get_channel_status(self, channel_id: str) -> str:
        """
        Get the status of a channel. Connect to database and check the status of the channel.
        Returns: Channel status if found, None otherwise.
        """
        # first ask the database
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return None
        return channel.status
    
    @ensure_session
    def get_kraus_id(self, channel_id: str) -> str:
        """
        Get the Kraus operator ID for a channel.
        Returns: Kraus ID if found, None otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return None
        return channel.kraus_id
    
    @ensure_session
    def get_vector_id(self, channel_id: str) -> str:
        """
        Get the entropy vector ID for a channel.
        Returns: Vector ID if found, None otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return None
        return channel.best_entropy_vector_id
    
    @ensure_session
    def get_channel_dimensions(self, channel_id: str) -> tuple:
        """
        Get the input and output dimensions of a channel.
        Returns: Tuple of input and output dimensions if found, None otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return None
        return channel.input_dimension, channel.output_dimension
    
    @ensure_session
    def get_num_kraus(self, channel_id: str) -> int:
        """
        Get the number of Kraus operators for a channel.
        Returns: Number of Kraus operators if found, None otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return None
        return channel.num_kraus
    
    @ensure_session
    def get_best_moe(self, channel_id: str) -> float:
        """
        Get the best MOE for a channel.
        Returns: Best MOE if found, None otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return None
        return channel.best_moe
    
    @ensure_session
    def get_minimization_attempts(self, channel_id: str) -> int:
        """
        Get the number of minimization attempts for a channel.
        Returns: Number of minimization attempts if found, None otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return None
        return channel.minimization_attempts
    
    @ensure_session
    def get_runs_spawned(self, channel_id: str) -> int:
        """
        Get the number of runs spawned for a channel.
        Returns: Number of runs spawned if found, None otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return None
        return channel.runs_spawned
    
    @ensure_session
    def get_runs_completed(self, channel_id: str) -> int:
        """
        Get the number of runs completed for a channel.
        Returns: Number of runs completed if found, None otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return None
        return channel.runs_completed
    
    ######################
    #      Setters       #
    ######################

    @ensure_session
    def set_channel_status(self, channel_id: str, status: str) -> bool:
        """
        Set the status of a channel. Connect to database and update the status of the channel.
        Returns: True if successful, False otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return False
        # Try to update status, if not possible, return False
        try:
            channel.status = status
            self.db.commit()
            return True
        except:
            return False
        
    @ensure_session
    def set_kraus_id(self, channel_id: str, kraus_id: str) -> bool:
        """
        Set the Kraus operator ID for a channel.
        Returns: True if successful, False otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return False
        # Try to update Kraus ID, if not possible, return False
        try:
            channel.kraus_id = kraus_id
            self.db.commit()
            return True
        except:
            return False

    @ensure_session
    def set_vector_id(self, channel_id: str, vector_id: str) -> bool:
        """
        Set the entropy vector ID for a channel.
        Returns: True if successful, False otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return False
        # Try to update Vector ID, if not possible, return False
        try:
            channel.best_entropy_vector_id = vector_id
            self.db.commit()
            return True
        except:
            return False

    @ensure_session
    def set_best_moe(self, channel_id: str, best_moe: float) -> bool:
        """
        Set the best MOE for a channel.
        Returns: True if successful, False otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return False
        # Try to update best MOE, if not possible, return False
        try:
            channel.best_moe = best_moe
            self.db.commit()
            return True
        except:
            return False

    @ensure_session
    def set_minimization_attempts(self, channel_id: str, minimization_attempts: int) -> bool:
        """
        Set the number of minimization attempts for a channel.
        Returns: True if successful, False otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return False
        # Try to update minimization attempts, if not possible, return False
        try:
            channel.minimization_attempts = minimization_attempts
            self.db.commit()
            return True
        except:
            return False        

    @ensure_session
    def increase_runs_spawned(self, channel_id : str, n : int =1) -> bool:
        """
        Increase the number of runs spawned by n.
        Returns: True if successful, False otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return False
        # Try to update minimization attempts, if not possible, return False
        try:
            channel.runs_spawned = channel.runs_spawned + n
            self.db.commit()
            return True
        except:
            return False        

    @ensure_session
    def increase_runs_completed(self, channel_id : str, n : int =1) -> bool:
        """
        Increase the number of runs completed by n.
        Returns: True if successful, False otherwise.
        """
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return False
        # Try to update minimization attempts, if not possible, return False
        try:
            channel.runs_completed = channel.runs_completed + n
            self.db.commit()
            return True
        except:
            return False        


    ######################
    #      Actions       #
    ######################

    @ensure_session
    def create_channel(self, input_dimension: int, output_dimension: int, num_kraus: int) -> str:
        """
        Create a new channel. Connect to database and create a new channel.
        Returns: Channel ID if successful, None otherwise.
        """
        # Create a new channel
        try:
            new_channel = Channel(input_dimension=input_dimension, output_dimension=output_dimension, num_kraus=num_kraus)
            self.db.add(new_channel)
            self.db.commit()
            self.db.refresh(new_channel)
            return new_channel.id
        except:
            return None
        
    @ensure_session
    def create_channel_from_kraus(self, kraus_id: str, input_dimension: int, output_dimension: int, num_kraus: int) -> str:
        """
        Create a new channel from a Kraus operator. Connect to database and create a new channel.
        Returns: Channel ID if successful, None otherwise.
        """
        # Create a new channel
        try:
            # Set the status to minimizing and the Kraus ID
            new_channel = Channel(kraus_id=kraus_id, input_dimension=input_dimension, output_dimension=output_dimension, num_kraus=num_kraus, status=ChannelStatusEnum.minimizing)
            self.db.add(new_channel)
            self.db.commit()
            self.db.refresh(new_channel)
            return new_channel.id
        except:
            return None
        
    def schedule_jobs(self) -> bool:
        """
        Schedule jobs for all channels. Connect to database and schedule jobs for all channels.
        Returns: True if successful, False otherwise.
        """
        print("Scheduling jobs for all channels...")
        # Get a session
        session = self._get_session()
        # Get all channels
        channels = session.query(Channel).all()

        # Schedule jobs for all channels
        for channel in channels:
            # If the channel is generating, schedule the corresponding generating job if not already done
            if channel.status == ChannelStatusEnum.created:
                # Step 1: schedule job for creating Kraus operator
                # TODO: implement different instructions for different types of channels? This should be stored in the channel info, and the job manager should also be updated
                # Get dimensions and number of kraus
                print("Trying to generate kraus operators for channel ", channel.id)
                data = {"input_dimension": channel.input_dimension, "output_dimension": channel.output_dimension, "number_kraus": channel.num_kraus, "channel_id": channel.id}
                print("Data: ", data)
                j = self.job_manager.create_job(job_type=JobType.generate_kraus, input_data=data, channel_id = channel.id)
                print("Job created: ", j)
                if not j:
                    print("Error while creating a job for generating kraus operators...")
                # Step 2: change channel status to generating. This DOES NOT UPDATE CHANNEL, only THE ROW IN THE DB!!!
                if not self.set_channel_status(channel_id=channel.id, status=ChannelStatusEnum.generating):
                    print("Error setting the channel status! Will cancel the job...")
                    self.job_manager.update_job_status(j.id, JobStatus.canceled)
                print(f"Scheduled job for generating kraus operators for channel {channel.id}...")
                continue

            # If the channel is minimizing, schedule a job
            # Also check how many runs have been spawned and completed and only spawn new runs if the number of runs spawned is less than the number of minimization attempts
            elif channel.status == ChannelStatusEnum.minimizing:
                print("Trying to check if I need to spawn more minimization runs for channel ", channel.id)
                # Check that we have more runs to spawn
                if channel.runs_spawned < channel.minimization_attempts:
                    #check that we haven't scheduled too many jobs
                    if channel.runs_spawned-channel.runs_completed < self.config.channel_max_jobs:
                        # There is space for spawning more!
                        jobs_to_spawn = channel.minimization_attempts - channel.runs_spawned
                        print(f"Need to spawn {jobs_to_spawn} more jobs for channel {channel.id}")
                        for i in range(min(jobs_to_spawn, self.config.channel_max_jobs)):
                            # Spawn a new minimizing job. This really is a job for creating a new vector...
                            data = {"input_dimension": channel.input_dimension, "channel_id": channel.id}
                            j = self.job_manager.create_job(job_type=JobType.generate_vector, input_data=data, channel_id = channel.id)
                            if not j:
                                # Something happened, break the loop. Job hasn't spawned so don't increase number of jobs
                                print("Failed to create a generate_vector job...")
                            # Increase the number of spawned runs by 1. THIS DOES NOT CHANGE THE CHANNEL, JUST THE ROW IN THE DB!!!
                            if not self.increase_runs_spawned(channel.id, 1):
                                print("Could not increase number of runs spawned, may end up running the algorithm too mnany times...")
                            print(f"Scheduled job for generating a vector for channel {channel.id}...")
                continue
        # clean up session
        session.close()

        return True
    
    def update_MOE(self):
        """
        Update the best MOE for all channels. Connect to database and update the best MOE for all channels.
        Returns: True if successful, False otherwise.
        """
        print("Updating MOE for all channels...")
        session = self._get_session()
        # Get all channels
        channels = session.query(Channel).all()
        if not channels:
            return False
        # Update MOE for all channels
        for channel in channels:
            # If the channel is minimizing (or is done), update the best MOE
            if channel.status == ChannelStatusEnum.minimizing or channel.status == ChannelStatusEnum.completed:
                # Get all jobs that this channel has spawned.
                jobs = session.query(Job).filter(Job.channel_id == channel.id).all()
                if not jobs:
                    print("No jobs found for channel ", channel.id)

                # Loop through all jobs and get the MOE
                for job in jobs:
                    # If the job is a minimization job, get its current entropy
                    if JobType(job.job_type) == JobType.minimize and job.status == JobStatus.completed:

                        # Get the entropy from the job
                        entropy = job.entropy
                        # If the entropy is less than the current MOE, update the entropy in the channel
                        # and update the vector. Do so only if the entropy is positive.
                        if (entropy < self.get_best_moe(channel.id) and entropy >= 0) or self.get_best_moe(channel.id) < 0:
                            # Update the best MOE
                            print(f"Channel {channel.id} has new best MOE: {entropy}. Updating the best MOE...")
                            if not self.set_best_moe(channel.id, entropy):
                                print("Error updating the best MOE...")
                                return False
                            # Update the vector ID
                            if not self.set_vector_id(channel.id, job.vector):
                                print("Error updating the best vector ID...")
                                return False
        print("Updated MOE for all channels...")


        # clean up session
        session.close()                
        return True

    def process_completed_jobs(self):
        """
        Process completed jobs in redis queue.
        1) If kraus creation is finished, update the channel with the kraus ID and set the status to minimizing.
        2) If minimization is happening:
            - If the completed job is a vector creation job, spawn a new minimization job with that vector.
            - If the completed job is a minimization job, update the best MOE and increment the number of runs completed.
            - If the number of runs completed is equal to the number of minimization attempts, set the channel status to completed.
        """           
        print("Processing completed jobs...")
        # Step 1: obtain all jobs in the redis queue
        while (jid := self.redis.lpop("to_process")) is not None:
            try:
                jid = int(jid)
            except ValueError:
                print("Error parsing job ID from redis queue...")
                continue
            # Get the job from the database
            type = self.job_manager.get_job_type(jid)
            if type:
                type = type["job_type"]
            else:
                print("Was trying to process completed job, but I found no job type for id ", jid)
            # Step 3: consider the various cases.
            if JobType(type) == JobType.generate_kraus:
                # Case 1. Job finished is generate_kraus. 
                #       -> Update the kraus info in the channel, and set the channel status to minimizing
                # Get the kraus ID from the job
                kraus_id = self.job_manager.get_kraus(jid)
                if kraus_id:
                    kraus_id = kraus_id["kraus_operator"]
                else:
                    print("Was trying to process completed job, but I found no kraus id for id ", jid)
                # Get the channel ID from the job
                channel_id = self.job_manager.get_channel(jid)
                if not channel_id:
                    print("Was trying to process completed job, but I found no channel id for id ", jid)
                try:
                    channel_id = channel_id["channel_id"]
                except:
                    print("Was trying to process completed job, but I found no channel id for id ", jid)

                # Update the channel with the kraus ID
                if not self.set_kraus_id(channel_id, kraus_id):
                    print("Error updating the channel with the kraus ID...")
                    print("Will reset the channel status to created, to reschedule creation job.")
                    self.set_channel_status(channel_id, ChannelStatusEnum.created)
                # Set the channel status to minimizing
                self.set_channel_status(channel_id, ChannelStatusEnum.minimizing)

            elif JobType(type) == JobType.generate_vector:
                # Case 2. Job finished is generate_vector.
                #       -> Spawn a new job of type "minimize" for that vector
                # Runs have already been increased
                # Get the vector ID from the job
                vector_id = self.job_manager.get_vector(jid)
                if vector_id:
                    vector_id = vector_id["vector"]
                else:
                    print("Was trying to process completed job, but I found no vector id for id ", jid)
                # Get the channel ID from the job
                channel_id = self.job_manager.get_channel(jid)
                if not channel_id:
                    print("Was trying to process completed job, but I found no channel id for id ", jid)
                try:
                    channel_id = channel_id["channel_id"]
                except:
                    print("Was trying to process completed job, but I found no channel id for id ", jid)
                # Get kraus ID
                kraus_id = self.get_kraus_id(channel_id)
                if not kraus_id:
                    print("Was trying to process completed job, but I found no kraus id for channel ", channel_id)
                
                # Spawn a new job of type minimize
                print("Spawning a new job for minimizing...")
                print("Passed parameters")
                print("Vector ID: ", vector_id)
                print("Channel ID: ", channel_id)
                print("Vector ID: ", vector_id)
                print("Kraus ID: ", kraus_id)

                data = {"input_dimension": self.get_channel_dimensions(channel_id)[0], "output_dimension": self.get_channel_dimensions(channel_id)[1], "number_kraus": self.get_num_kraus(channel_id), "channel_id": channel_id}
                j = self.job_manager.create_job(job_type=JobType.minimize, input_data=data, vector=vector_id, kraus_operators=kraus_id, channel_id = channel_id)
                if not j:
                    print("Error creating a new job for minimizing...")

            elif JobType(type) == JobType.minimize:
                # Case 3. Job finished is minimize.
                #       -> Increase runs_completed by 1
                #       -> If runs_completed == minimization_attempts, set channel status to completed.
                # Get the channel ID from the job
                channel_id = self.job_manager.get_channel(jid)
                if not channel_id:
                    print("Was trying to process completed job, but I found no channel id for id ", jid)
                try:
                    channel_id = channel_id["channel_id"]
                except:
                    print("Was trying to process completed job, but I found no channel id for id ", jid)
                # Increase the number of runs completed
                if not self.increase_runs_completed(channel_id):
                    print("Error increasing the number of runs completed...")
                # Check if we have reached the number of minimization attempts
                if self.get_runs_completed(channel_id) == self.get_minimization_attempts(channel_id):
                    # Set the channel status to completed
                    self.set_channel_status(channel_id, ChannelStatusEnum.completed)
                    print(f"Channel {channel_id} has completed minimization.")
        return True
    
    async def update(self):
        while True:
            try:
                # Schedule jobs if needed
                if not self.schedule_jobs():
                    print("Error scheduling jobs...")
                
                # Process completed jobs
                if not self.process_completed_jobs():
                    print("Error processing completed jobs...")

                # Update MOE
                if not self.update_MOE():
                    print("Error updating MOE...")

                # Make sure the job manager manages jobs
                self.job_manager.manage_jobs()

            except Exception as e:
                print(f"Exception in update(): {e}")

            # Sleep for a while
            await asyncio.sleep(self.config.update_interval)
            


# instantiate a channel manager
channel_manager = ChannelManager()
