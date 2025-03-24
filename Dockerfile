# Use the official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY ./requirements.txt /app/

# Install system dependencies and upgrade pip
RUN apt-get update && apt-get install -y libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies separately to optimize caching
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --user --no-warn-script-location -r requirements.txt

# Copy the rest of the application (AFTER installing dependencies)
COPY ./app /app



# Run the FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]