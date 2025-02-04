# 1. main.py (Entry Point)
from fastapi import FastAPI
from app.api import users

app = FastAPI()
app.include_router(users.router)

@app.get("/")
def read_root():
    return {"message": "QuantumHive API is running!"}