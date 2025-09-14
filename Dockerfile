# Use Python 3.13 official image as base
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install uv package manager
RUN pip install uv

# Install project dependencies using uv
RUN uv sync --frozen

# Expose port for potential web interface (FastAPI is in dependencies)
EXPOSE 8000

# Create directories for data and logs
RUN mkdir -p data logs

# Create a non-root user and switch to it
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONPATH=/app

# Default command to run the application in scheduler mode
CMD ["uv", "run", "python", "-m", "app.main", "--mode", "schedule"]