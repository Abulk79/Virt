# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies needed for the application
RUN pip install --no-cache-dir \
    asyncpg==0.29.0 \
    alembic==1.13.1 \
    python-dotenv==1.1.0

# Copy the application code
COPY . .

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
# Expose the port the app runs on
EXPOSE 8080

# Use the startup script as the default command
CMD ["/app/start.sh"] 