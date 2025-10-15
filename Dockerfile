# Use full Python image to avoid missing pyaudioop
FROM python:3.13

# Install system dependencies including ffmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg libasound2-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port for FastAPI
EXPOSE 10000

# Start FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
