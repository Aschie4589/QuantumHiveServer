# Use the official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents (that are relevant) into the container
COPY ./app ./app
COPY ./requirements.txt /app

# Install the latest version of pip
RUN pip install --no-cache-dir --upgrade pip

# Install the required system packages
RUN apt-get update
RUN apt-get install -y libpq-dev gcc

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Ensure Python can find the `app` module
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]