from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Get the password from the Docker secret (at /run/secrets/db_password)
with open("/run/secrets/db_password", "r") as file:
    db_password = file.read().strip()

# Database URL
DATABASE_URL = f"postgresql://quantumhive:{db_password}@db:5432/quantumhive"
print("Database URL: ", DATABASE_URL)
print("Database password: ", db_password)
# Create the database engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base() # Base class for the ORM models (to be inherited by the models)

# Dependency to get the database session (called in the API endpoints to get the database session)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()