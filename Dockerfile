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
RUN echo '#!/bin/bash\n\
set -a\n\
source /etc/environment\n\
set +a\n\
cd /app && /usr/local/bin/python weekly_job.py\n' > /app/run_weekly_job.sh && \
    chmod +x /app/run_weekly_job.sh

# Setup cron job - runs wrapper script
RUN echo "0 0 * * 1 /app/run_weekly_job.sh >> /var/log/trustpilot-cron.log 2>&1" > /etc/cron.d/weekly-job && \
    chmod 0644 /etc/cron.d/weekly-job && \
    crontab /etc/cron.d/weekly-job && \
    touch /var/log/trustpilot-cron.log

# Start cron in foreground and tail the log
CMD ["/bin/bash", "-c", "printenv | grep -v 'no_proxy' | sed 's/=/=\"/' | sed 's/$/\"/' >> /etc/environment && cron && tail -f /var/log/trustpilot-cron.log"]