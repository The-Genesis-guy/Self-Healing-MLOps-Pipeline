# Backend Dockerfile for GUARDIAN
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only python requirements first for caching
COPY requirements-pinned.txt ./
RUN pip install --no-cache-dir -r requirements-pinned.txt

# Copy application code
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
