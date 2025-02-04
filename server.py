from fastapi import FastAPI, HTTPException, Depends, Header, Form # Importing FastAPI and HTTPException. This is the main class that will be used to define the API.
from dotenv import load_dotenv # Importing load_dotenv from the dotenv module. This will be used to load the API key from the .env file.
import jwt # Importing jwt from the PyJWT module. This will be used to generate and verify JWT tokens. 
import os 
import datetime
import redis # Importing redis module. This will be used to store the refresh tokens in a Redis database.


# FIRST START REDIS USING brew services start redis


# Load SECRET key from .env file
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_123456")

app = FastAPI()

# JWT Settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token expiration in minutes
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Refresh token expiration in days

# Redis Settings
# Connect to Redis
#TODO: This is not secure as redis is in theory exposed to the internet. Use a more secure method to connect to Redis? Change this.
redis_client = redis.Redis(host="redis", port=6379, db=0)

# ------------------------------
# Authentication Functions
# ------------------------------

# We use an auth and refresh token system. The access token is short-lived and the refresh token is long-lived.
# The access token is used to authenticate the user for a short period of time (e.g. 15 mins) and the refresh token is used to get a new access token when the old one expires.

# Create a token. Data will contain "type" (access or refresh) and "sub" (subject, e.g. username).
def create_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # JWT token is of the form Header.Payload.Signature, and Payload contains the data in JSON format. Can be any data.
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Verify JWT token and extract user info
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Dependency to get the payload from token
def get_current_user(authorization: str = Header(...)):
    # FastAPI reads the name of the variable above ("authorization") and looks for a header with the same name. Underscores become dashes.
    # Get the token from the Authorization header (Bearer <token>)
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Invalid authentication header format")
    token = authorization[7:]  # Extract the token part
    # Check if the token is revoked
    if is_token_revoked(token):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    pl = verify_token(token) # This returns the token payload if token is valid
    # check that the token is an access token
    if pl["type"] != "access":
        raise HTTPException(status_code=400, detail="Invalid token type")
    return pl

def revoke_token(token: str):
    redis_client.setex(f"blacklist:{token}", REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, "revoked")
    # Log the revoked token
    print(f"Revoked token: {token}")

def is_token_revoked(token: str):
    print("Checking if token is revoked")
    return redis_client.exists(f"blacklist:{token}")

# ----------------------------
# Routes
# ----------------------------

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    # Validate the username and password (this can be improved) TODO: improve this!
    if username == "client" and password == "password123":  # Dummy validation
        # Create tokens and send them to user.
        access_token = create_token(data={"sub": username, "type": "access"})
        refresh_token = create_token(data={"sub": username, "type": "refresh"}, expires_delta=datetime.timedelta(days=30))
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/refresh")
# refresh the access token. Refresh is included as Header in the request.
def refresh_token(refresh: str = Header(...)):
    # Verify the refresh token
    payload = verify_token(refresh)
    if payload["type"] != "refresh":
        raise HTTPException(status_code=400, detail="Invalid token type")
    # Check if the token is revoked
    if is_token_revoked(refresh):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    # Next revoke the refresh token
    revoke_token(refresh)
    print("Have revoked token, now creating new token (refresh)")
    # Create a new access token and return it. Rotate the refresh token.
    access_token = create_token(data={"sub": payload["sub"], "type": "access"})
    refresh_token = create_token(data={"sub": payload["sub"], "type": "refresh"}, expires_delta=datetime.timedelta(days=30))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.get("/status")
def status(current_user: dict = Depends(get_current_user)):
    # Dummy status info. Add user.
    return {
        "status": "Server is running",
        "user": current_user["sub"]
    }

@app.get("/")
def root():
    return {"message": "Quantum Optimization Server Running 🚀"}

