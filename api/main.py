# Main FastAPI application entry point

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import pipeline, models, drift

app = FastAPI(
    title="Self-Healing MLOps Pipeline API",
    description="Monitor and control the self-healing ML pipeline",
    version="1.0.0"
)

# Allow the React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline.router)
app.include_router(models.router)
app.include_router(drift.router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "self-healing-mlops-api"}
