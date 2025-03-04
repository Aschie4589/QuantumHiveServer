from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# Get the password from the Docker secret (at /run/secrets/db_password)
with open("/run/secrets/db_password", "r") as file:
    db_password = file.read().strip()

# Database URL
DATABASE_URL = f"postgresql://quantumhive:{db_password}@db:5432/quantumhive"

# Create the database engine
engine = create_engine(DATABASE_URL)
SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base() # Base class for the ORM models (to be inherited by the models)

# Dependency to get the database session (called in the API endpoints to get the database session)
def get_db():
    """Creates and provides a session for each request."""
    session = SessionFactory()  # Retrieve the session bound to this request's scope
    try:
        yield session  # Return session to the caller
        session.commit()  # Commit changes after processing the request
    except:
        session.rollback()  # Rollback on error
        raise  # Re-raise the exception
    finally:
        session.close()  # Automatically removes session after request finishes