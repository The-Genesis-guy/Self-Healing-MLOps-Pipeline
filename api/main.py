"""Main FastAPI application entry point

Adds environment-configured CORS and a Prometheus `/metrics` endpoint.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Summary
from api.routes import pipeline, models, drift

# Load environment variables from .env if present
load_dotenv()

APP_TITLE = os.getenv("APP_TITLE", "Self-Healing MLOps Pipeline API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

app = FastAPI(
    title=APP_TITLE,
    description="Monitor and control the self-healing ML pipeline",
    version=APP_VERSION,
)

# Configure CORS origins via environment variable (comma-separated)
allowed = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
allowed = [u.strip() for u in allowed if u.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline.router)
app.include_router(models.router)
app.include_router(drift.router)

# Simple Prometheus summary to observe request durations
REQUEST_LATENCY = Summary("api_request_latency_seconds", "API request latency in seconds", ['path'])


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    with REQUEST_LATENCY.labels(path=path).time():
        response = await call_next(request)
    return response


@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "self-healing-mlops-api"}
