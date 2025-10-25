# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 bankapi && chown -R bankapi:bankapi /app
USER bankapi

# Expose port
EXPOSE 5025

# Default command (can be overridden in docker-compose)
CMD ["gunicorn", "--bind", "0.0.0.0:5025", "--workers", "4", "--timeout", "120", "run:app"]

