# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create directory for credentials if it doesn't exist
RUN mkdir -p /app/sheets

# Make scripts executable
RUN chmod +x weekly_job.py preflight_check.py

# Container stays alive, waiting for commands
CMD ["tail", "-f", "/dev/null"]