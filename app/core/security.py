from passlib.context import CryptContext
import jwt # Importing jwt from the PyJWT module. This will be used to generate and verify JWT tokens. 
import datetime
from fastapi import HTTPException, Header # Importing Header and HTTPException. 
from redis import Redis
# Here we handle security functions. We check passwords and we issue/revoke tokens.


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # Password hashing context. 


# JWT Settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token expiration in minutes
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Refresh token expiration in days
# Load SECRET key from Docker environment
with open("/run/secrets/jwt_secret", "r") as f:
    SECRET_KEY = f.read().strip()



# Redis Settings
# Connect to Redis
# TODO: Can we make this more secure? Redis is exposed to the internet.
redis_client = Redis(host="redis", port=6379, db=0)

# ------------------------------
# Authentication Functions
# ------------------------------

# We use an auth and refresh token system. The access token is short-lived and the refresh token is long-lived.
# The access token is used to authenticate the user for a short period of time (e.g. 15 mins) and the refresh token is used to get a new access token when the old one expires.

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

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