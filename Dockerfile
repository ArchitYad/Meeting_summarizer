# Use official Python image
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port that FastAPI uses
EXPOSE 10000

# Start FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
