FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for compiling python dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port
EXPOSE 8000

# Set environment variable defaults
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=development

# By default, run uvicorn with reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
