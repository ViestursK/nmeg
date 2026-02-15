# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including cron
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

# Create directory for credentials
RUN mkdir -p /app/sheets

# Make scripts executable
RUN chmod +x weekly_job.py preflight_check.py

# Create wrapper script that loads environment
RUN echo '#!/bin/sh\n\
export DB_HOST="$DB_HOST"\n\
export DB_PORT="$DB_PORT"\n\
export DB_NAME="$DB_NAME"\n\
export DB_USER="$DB_USER"\n\
export DB_PASS="$DB_PASS"\n\
export GOOGLE_DRIVE_FOLDER_ID="$GOOGLE_DRIVE_FOLDER_ID"\n\
export GOOGLE_SHEETS_CREDENTIALS="$GOOGLE_SHEETS_CREDENTIALS"\n\
export MASTER_SPREADSHEET_NAME="$MASTER_SPREADSHEET_NAME"\n\
export TRUSTPILOT_JWT="$TRUSTPILOT_JWT"\n\
cd /app && /usr/local/bin/python weekly_job.py\n' > /app/run_weekly_job.sh && \
    chmod +x /app/run_weekly_job.sh

# Setup cron job - runs wrapper script
RUN echo "0 0 * * 1 /app/run_weekly_job.sh >> /var/log/trustpilot-cron.log 2>&1" > /etc/cron.d/weekly-job && \
    chmod 0644 /etc/cron.d/weekly-job && \
    crontab /etc/cron.d/weekly-job && \
    touch /var/log/trustpilot-cron.log

# Start cron in foreground and tail the log
CMD cron && tail -f /var/log/trustpilot-cron.log