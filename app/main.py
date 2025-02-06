from app import app
# Import and include your routers
from app.api.v1.endpoints import users, auth
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import engine, Base


app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router, prefix="/auth", tags=["jobs"])

# Create DB tables (if they don’t exist)
Base.metadata.create_all(bind=engine)


# CORS (Allow frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.get("/")
def read_root():
    return {"message": "QuantumHive API is running!"}



# Run with: uvicorn app.main:app --host 0.0.0.0 --port 8000