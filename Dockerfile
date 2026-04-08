# Use official lightweight Python 3.11 runtime as a parent image
FROM python:3.11-slim

# Set strict environment variables for Python runtime behavior:
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disk
# PYTHONUNBUFFERED: Prevents Python from buffering stdout/stderr, ensuring logs are flushed immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory mapping
WORKDIR /app

# Install system dependencies required for C-extensions and building Python packages (e.g., cryptography, passlib)
# Cleans up apt cache afterwards to minimize the final image layer size
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Leverage Docker layer caching by copying requirements.txt independently
# This prevents rebuilding the dependency layer if only the application code changes
COPY requirements.txt ./requirements.txt

# Upgrade pip and install Python dependencies without caching wheel files to optimize image size
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application source code into the corresponding package directory
# Placed in /app/api to resolve the application's absolute imports (e.g., `from api.models.base import Base`)
COPY . /app

# Enforce least privilege security best practices
# Create a non-privileged system user and assign ownership of the working directory
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose the designated port for the ASGI server
EXPOSE 8000

# Define the container's entrypoint instruction running the Uvicorn ASGI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
