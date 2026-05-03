# LAYER 2: API & Data Management Documentation

**FastAPI Backend + Pydantic Schemas + SQLite Persistence**

This document details the complete API architecture, endpoint specifications, request/response formats, database schemas, and data management strategies of the GUARDIAN backend.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [FastAPI Setup](#fastapi-setup)
5. [Core Endpoints](#core-endpoints)
6. [Request/Response Schemas](#requestresponse-schemas)
7. [State Management](#state-management)
8. [Database Design](#database-design)
9. [Error Handling](#error-handling)
10. [Authentication & Security](#authentication--security)
11. [Performance & Caching](#performance--caching)
12. [Development & Testing](#development--testing)

---

## Architecture Overview

The API layer sits between the frontend dashboard and the core pipeline logic. It provides:

1. **REST Endpoints**: HTTP/JSON interface for frontend consumption
2. **Background Process**: Threaded pipeline loop running independently
3. **State Management**: Shared state between API and pipeline loop
4. **Data Persistence**: SQLite database for history and model registry
5. **Request Validation**: Pydantic schemas for type safety
6. **Observability**: Prometheus scrape endpoint plus a JSON view for the dashboard

### Communication Flow

```
┌──────────────────┐
│  React Dashboard │
│  (Layer 1)       │
└────────┬─────────┘
         │ HTTP/JSON
         ↓
┌──────────────────────────────────────┐
│       FastAPI Backend (Layer 2)       │
│  - /pipeline endpoints                │
│  - /models endpoints                  │
│  - /metrics + /metrics/json           │
│  - Global state management            │
└────────┬─────────────────────────────┘
         │ Function calls
         ↓
┌──────────────────┐
│  Core Pipeline   │
│  (Layer 3)       │
└──────────────────┘
         │
         ↓
┌──────────────────────────────────────┐
│     SQLite Databases                  │
│  - history.db (event log)             │
│  - registry.json (model registry)     │
└──────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI | Modern async Python API |
| Server | Uvicorn | ASGI server |
| Validation | Pydantic v2 | Request/response validation |
| Database | SQLite | Event persistence |
| Threading | Python threading | Background pipeline loop |
| JSON | Standard library | Serialization |

### Configuration

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="GUARDIAN Pipeline API",
    description="Self-healing MLOps pipeline backend",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Dev frontend
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Project Structure

```
api/
├── __init__.py
├── main.py                 # FastAPI app & startup
├── runner.py               # Pipeline loop (threaded)
├── state.py                # Global shared state
├── schemas.py              # Pydantic request/response models
└── routes/
    ├── __init__.py
    ├── pipeline.py         # /pipeline/* endpoints
    ├── models.py           # /models endpoints
    └── drift.py            # /pipeline/drift endpoint (future)

Key Files:
- main.py: 50 lines, app setup & startup/shutdown events
- runner.py: 200 lines, pipeline loop with decision logic
- state.py: 100 lines, global state dataclass
- schemas.py: 150 lines, Pydantic models
```

---

## FastAPI Setup

### Application Initialization

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.runner import start as start_pipeline, stop as stop_pipeline

app = FastAPI(
    title="GUARDIAN Pipeline API",
    description="Self-healing MLOps pipeline backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Dev
        "http://localhost:8000",      # Local
        # Production domains would go here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(pipeline_router, prefix="/pipeline")
app.include_router(models_router, prefix="/models")

### Convenience entrypoint

The repository includes `api/__main__.py` which wraps `uvicorn` so you can start the API with:

```bash
# from repo root
python3 -m api
```

This is equivalent to running `python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000`.
```

### Startup & Shutdown Events

```python
@app.on_event("startup")
async def startup():
    """Initialize resources and start background pipeline"""
    pipeline_state.update(running=True)
    start_pipeline()  # Threaded
    print("✅ Pipeline started")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup resources"""
    stop_pipeline()
    pipeline_state.update(running=False)
    print("⏹️ Pipeline stopped")
```

### Health Check Endpoint

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "running": pipeline_state.running
    }
```

---

## Core Endpoints

### 1. GET /pipeline/status

**Purpose**: Retrieve current pipeline state

**Request**:
```
GET /pipeline/status
```

**Response** (200 OK):
```json
{
  "running": true,
  "iteration": 864,
  "last_action": "none",
  "last_reason": "No drift detected and model performance is acceptable",
  "last_drifted_features": [],
  "active_model_version": 1,
  "active_model_f1": 0.5085,
  "shadow_model_version": null,
  "health": "healthy"
}
```

**Fields**:
- `running` (bool): Pipeline loop is active
- `iteration` (int): Current iteration number
- `last_action` (str): Latest decision action
- `last_reason` (str): Human-readable explanation
- `last_drifted_features` (list[str]): Features triggering drift
- `active_model_version` (int|null): Current production model
- `active_model_f1` (float|null): Current model's F1-Score
- `shadow_model_version` (int|null): Model in trial (if any)
- `health` (str): "healthy" | "warning" | "critical"

**Implementation**:
```python
@pipeline_router.get("/status", response_model=PipelineStatusResponse)
async def get_status():
    return pipeline_state.dict()
```

**Response Time**: ~50ms

---

### 2. GET /pipeline/history

**Purpose**: Retrieve event log with optional filtering

**Request**:
```
GET /pipeline/history?limit=100
```

**Query Parameters**:
- `limit` (int, default=100): Max entries to return (max 1000)

**Response** (200 OK):
```json
[
  {
    "iteration": 864,
    "timestamp": "2026-05-02T18:19:45.109141",
    "model_version": 1,
    "f1_score": 0.5085,
    "drift_score": 0.0,
    "action": "none",
    "reason": "No drift detected and model performance is acceptable"
  },
  {
    "iteration": 863,
    "timestamp": "2026-05-02T18:19:40.088108",
    "model_version": 1,
    "f1_score": 0.5085,
    "drift_score": 0.0,
    "action": "none",
    "reason": "No drift detected and model performance is acceptable"
  },
  ...
]
```

**Fields** (per entry):
- `iteration` (int): Pipeline iteration number
- `timestamp` (str): ISO 8601 timestamp
- `model_version` (int|null): Model version used
- `f1_score` (float|null): Model's F1-Score at time
- `drift_score` (float): Maximum PSI across features
- `action` (str): Decision action taken
- `reason` (str): Explanation of action

**Possible Actions**:
- `"none"` - Pipeline stable, no action needed
- `"retrain"` - Retrain triggered (drift detected)
- `"rollback"` - Revert to previous model (performance drop)
- `"promote"` - Promote shadow model to active
- `"shadow"` - Candidate model in trial
- `"alert"` - Mild drift detected (informational)
- `"safe_mode"` - Circuit breaker triggered
- `"failed_retrain"` - Retraining failed

**Implementation**:
```python
@pipeline_router.get("/history", response_model=list[HistoryEntryResponse])
async def get_history(limit: int = 100):
    history = HistoryLogger()
    entries = history.get_recent(min(limit, 1000))
    return [HistoryEntryResponse(**entry.dict()) for entry in entries]
```

**Response Time**: ~100ms (disk I/O)

---

### 3. GET /models

**Purpose**: Retrieve model registry with version history

**Request**:
```
GET /models
```

**Response** (200 OK):
```json
[
  {
    "version": 1,
    "path": "models/v1.pkl",
    "f1_score": 0.5085,
    "trained_at": "2026-04-30T23:52:50.239906",
    "is_active": true,
    "feature_importance": {
      "transaction_amount": 0.29,
      "distance_from_home": 0.24,
      "oldBalanceOrg": 0.18,
      "newBalanceDest": 0.14,
      "hour_of_day": 0.09,
      "is_foreign": 0.06
    }
  },
  {
    "version": 2,
    "path": "models/v2.pkl",
    "f1_score": 0.5085,
    "trained_at": "2026-04-30T23:53:04.359832",
    "is_active": false,
    "feature_importance": null
  },
  ...
]
```

**Fields** (per model):
- `version` (int): Unique version identifier
- `path` (str): File path to model pickle
- `f1_score` (float): Performance metric
- `trained_at` (str): ISO 8601 timestamp
- `is_active` (bool): Currently serving predictions
- `feature_importance` (dict|null): Feature weights

**Ordering**: By version descending (newest first)

**Implementation**:
```python
@models_router.get("", response_model=list[ModelResponse])
async def get_models():
    registry = ModelRegistry()
    models = registry.get_all()
    return [ModelResponse.from_orm(m) for m in models]
```

**Response Time**: ~80ms

---

### 4. GET /metrics

**Purpose**: Expose Prometheus text format for external scraping

**Request**:
```http
GET /metrics
```

**Response**:
- Prometheus exposition format
- Includes default Python process metrics and `api_request_latency_seconds`

**Implementation**:
```python
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

### 5. GET /metrics/json

**Purpose**: Return structured Prometheus metrics for the dashboard UI

**Request**:
```http
GET /metrics/json
```

**Response** (200 OK):
```json
{
    "metrics": [
        {
            "name": "api_request_latency_seconds",
            "type": "summary",
            "help": "API request latency in seconds",
            "samples": [
                {
                    "name": "api_request_latency_seconds_count",
                    "labels": { "path": "/pipeline/status" },
                    "value": 76
                }
            ]
        }
    ]
}
```

**Dashboard Usage**:
- The React dashboard polls this endpoint every 2 seconds alongside `/pipeline/status`, `/pipeline/history`, and `/models`.
- It displays a compact metrics feed with family count, sample count, request count, and derived average latency.

**Implementation Notes**:
- The JSON response is derived from the Prometheus registry using sample parsing.
- The endpoint is intentionally read-only and safe to expose to the dashboard.

---

### 6. POST /pipeline/start

**Purpose**: Start the pipeline loop

**Request**:
```
POST /pipeline/start
Content-Type: application/json

{
  "scenario": "normal"
}
```

**Request Body**:
```python
class StartPipelineRequest(BaseModel):
    scenario: str  # "normal", "night_shift", "high_value", etc.
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Pipeline started successfully"
}
```

**Error Responses**:
- 409 Conflict: Pipeline already running

**Implementation**:
```python
@pipeline_router.post("/start", response_model=ActionResponse)
async def start_pipeline(request: StartPipelineRequest):
    if pipeline_state.running:
        raise HTTPException(status_code=409, detail="Pipeline already running")
    
    runner.start(adapter_selector(request.scenario))
    return ActionResponse(success=True, message="Pipeline started")
```

---

### 5. POST /pipeline/stop

**Purpose**: Stop the pipeline loop

**Request**:
```
POST /pipeline/stop
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Pipeline stopped successfully"
}
```

**Implementation**:
```python
@pipeline_router.post("/stop", response_model=ActionResponse)
async def stop_pipeline():
    runner.stop()
    return ActionResponse(success=True, message="Pipeline stopped")
```

---

## Request/Response Schemas

### Pydantic Models (api/schemas.py)

All request/response validation uses Pydantic v2 for type safety and automatic OpenAPI documentation.

```python
from pydantic import BaseModel, Field
from typing import Optional

# Request Models
class StartPipelineRequest(BaseModel):
    scenario: str

# Response Models
class PipelineStatusResponse(BaseModel):
    running: bool
    iteration: int
    last_action: str
    last_reason: str
    last_drifted_features: list[str]
    active_model_version: Optional[int]
    active_model_f1: Optional[float]
    shadow_model_version: Optional[int] = None
    health: str

class HistoryEntryResponse(BaseModel):
    iteration: int
    timestamp: str
    model_version: Optional[int]
    f1_score: Optional[float]
    drift_score: float
    action: str
    reason: str

class ModelResponse(BaseModel):
    version: int
    path: str
    f1_score: float
    trained_at: str
    is_active: bool
    feature_importance: Optional[dict] = None

class DriftFeatureReport(BaseModel):
    feature: str
    psi_score: float
    drifted: bool

class DriftReportResponse(BaseModel):
    scenario: str
    features: list[DriftFeatureReport]

class ActionResponse(BaseModel):
    success: bool
    message: str
```

### Validation Rules

- **String fields**: Non-empty, trimmed
- **Numeric fields**: Type-checked, range-validated
- **Optional fields**: Can be null or omitted
- **Enums**: Strict value matching

**Auto-Generated OpenAPI**:
```
GET http://localhost:8000/docs
```

Provides interactive Swagger UI for testing all endpoints.

---

## State Management

### Global State (api/state.py)

Shared state between FastAPI endpoints and background pipeline loop.

```python
from dataclasses import dataclass, field

@dataclass
class PipelineState:
    """Thread-safe shared state"""
    
    # Pipeline Status
    running: bool = False
    iteration: int = 0
    
    # Latest Decision
    last_action: str = "none"
    last_reason: str = "Pipeline waiting to start"
    last_drifted_features: list[str] = field(default_factory=list)
    
    # Model Status
    active_model_version: Optional[int] = None
    active_model_f1: Optional[float] = None
    shadow_model_version: Optional[int] = None
    
    # Health Status
    health: str = "healthy"  # "healthy", "warning", "critical"
    
    def update(self, **kwargs):
        """Safely update state fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

# Singleton instance
pipeline_state = PipelineState()
```

### Thread Safety

State updates are protected with minimal locking:

```python
# In pipeline loop (runner.py)
pipeline_state.update(
    iteration=iteration,
    last_action=decision.action,
    last_reason=decision.reason,
    last_drifted_features=drifted
)
```

No explicit locks needed because:
1. Field assignments are atomic in Python
2. GIL (Global Interpreter Lock) protects reference assignments
3. No complex concurrent modifications

---

## Developer: Running the API & Tests

Install backend dependencies and run the API locally:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start API (convenience wrapper)
python3 -m api

# or start directly with Uvicorn
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Run the backend end-to-end tests locally:

```bash
pytest -q tests/e2e
```

Notes:
- `requirements.txt` includes `httpx` which is required by `fastapi.testclient` and some tests.
- The CI workflow (`.github/workflows/ci.yml`) starts the backend with a background `uvicorn` command and installs Playwright browsers before running the dashboard tests.


## Database Design

### History Database (models/history.db)

SQLite database storing all pipeline events for audit trail and visualization.

**Schema**:
```sql
CREATE TABLE history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    iteration       INTEGER NOT NULL,
    model_version   INTEGER,
    f1_score        REAL,
    drift_score     REAL,
    action          TEXT,
    reason          TEXT
);
```

**Indexes**:
```sql
CREATE INDEX idx_iteration ON history(iteration DESC);
CREATE INDEX idx_timestamp ON history(timestamp DESC);
CREATE INDEX idx_action ON history(action);
```

**Record Format**:
- `timestamp`: ISO 8601 (e.g., "2026-05-02T18:19:45.109141")
- `iteration`: Sequential counter starting from 1
- `model_version`: FK to model registry (nullable)
- `f1_score`: Performance metric (nullable)
- `drift_score`: Max PSI across all features
- `action`: Enum (none, retrain, alert, promote, etc.)
- `reason`: Human-readable explanation

**Total Records**: 2,120+ (at ~1 per 5 seconds)
**Disk Size**: ~1MB
**Query Performance**: <50ms for limit=100

**Insertion Pattern**:
```python
# From core/history.py
conn.execute("""
    INSERT INTO history (timestamp, iteration, model_version, f1_score, drift_score, action, reason)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (timestamp, iteration, version, f1, drift, action, reason))
conn.commit()
```

### Model Registry (models/registry.json)

JSON file storing model metadata (version, path, metrics, importance).

**Structure**:
```json
{
  "models": [
    {
      "version": 1,
      "path": "models/v1.pkl",
      "f1_score": 0.5085,
      "trained_at": "2026-04-30T23:52:50.239906",
      "is_active": true,
      "feature_importance": {...}
    },
    ...
  ],
  "active_version": 1,
  "total_versions": 13
}
```

**Access Pattern**:
1. Read JSON on startup
2. Update in memory (fast)
3. Write back to disk after model changes

**Consistency**: File-level locking on write operations

---

## Error Handling

### HTTP Status Codes

| Code | Scenario |
|------|----------|
| 200 | Successful request |
| 400 | Bad request (validation error) |
| 404 | Resource not found |
| 409 | Conflict (e.g., pipeline already running) |
| 500 | Server error |

### Error Response Format

```python
# Automatic from FastAPI/Pydantic
{
  "detail": "Pipeline already running"
}

# Custom exception
raise HTTPException(
    status_code=409,
    detail="Pipeline is already running"
)
```

### Common Error Scenarios

**Pipeline Already Running**:
```
Status: 409 Conflict
Detail: "Pipeline is already running"
```

**Invalid Model Version**:
```
Status: 404 Not Found
Detail: "Model version not found"
```

**Database Connection Error**:
```
Status: 500 Internal Server Error
Detail: "Database connection failed"
```

### Logging

Errors logged with context for debugging:

```python
import logging

logger = logging.getLogger(__name__)

try:
    # Operation
except Exception as e:
    logger.error(f"Operation failed: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e))
```

---

## Authentication & Security

### Current Implementation

**No Authentication Required** (local development)

### Production Recommendations

For production deployment:

1. **API Key Authentication**
   ```python
   from fastapi.security import HTTPBearer, HTTPAuthCredentials
   
   security = HTTPBearer()
   
   @app.get("/status")
   async def get_status(credentials: HTTPAuthCredentials = Depends(security)):
       if credentials.credentials != os.getenv("API_KEY"):
           raise HTTPException(status_code=403)
   ```

2. **JWT Tokens**
   ```python
   from jose import JWTError, jwt
   
   def verify_token(token: str):
       try:
           payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
           return payload
       except JWTError:
           raise HTTPException(status_code=401)
   ```

3. **HTTPS/TLS**
   - Use uvicorn with SSL certificates
   - Enforce HTTPS in production

4. **Rate Limiting**
   ```python
   from slowapi import Limiter
   
   limiter = Limiter(key_func=get_remote_address)
   
   @app.get("/status")
   @limiter.limit("60/minute")
   async def get_status():
       ...
   ```

---

## Performance & Caching

### Response Times

Measured on MacBook (2.6GHz):

| Endpoint | Time | Factors |
|----------|------|---------|
| /status | 50ms | In-memory state |
| /models | 80ms | JSON I/O |
| /history | 100ms | SQLite query |
| /start | 200ms | Process spawning |

### Caching Strategy

**Frontend Caching**:
- 2-second refresh interval
- Browser caches GET responses
- No aggressive caching to preserve freshness

**Backend Caching**:
- Model registry cached in memory
- History table indexed on iteration, timestamp
- No application-level caching layer (SQLite handles it)

### Optimization Tips

1. **Limit Query Results**: Always use `limit` parameter
   ```python
   GET /pipeline/history?limit=100
   ```

2. **Bulk Operations**: Fetch all required data in single request
   - Don't fetch /status, then /history, then /models separately
   - Frontend does this with Promise.all

3. **Index Usage**: Ensure database indexes on frequently-queried columns
   ```sql
   CREATE INDEX idx_iteration ON history(iteration DESC);
   ```

---

## Development & Testing

### Running the API

**Development Mode**:
```bash
# Terminal 1: Start FastAPI server
python3 -m api.main

# Server runs on http://localhost:8000
# Auto-reload on file changes
# API docs: http://localhost:8000/docs
```

**Production Mode**:
```bash
# With gunicorn (multiple workers)
gunicorn -w 4 -b 0.0.0.0:8000 api.main:app
```

### Testing Endpoints

**Using curl**:
```bash
# Get status
curl http://localhost:8000/pipeline/status

# Get history
curl http://localhost:8000/pipeline/history?limit=10

# Get models
curl http://localhost:8000/models

# Start pipeline
curl -X POST http://localhost:8000/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"scenario": "normal"}'

# Stop pipeline
curl -X POST http://localhost:8000/pipeline/stop
```

**Using Python requests**:
```python
import requests

# Get status
response = requests.get("http://localhost:8000/pipeline/status")
print(response.json())

# Start pipeline
response = requests.post(
    "http://localhost:8000/pipeline/start",
    json={"scenario": "normal"}
)
print(response.json())
```

**Interactive Testing**:
```
Open http://localhost:8000/docs in browser
→ Swagger UI for testing all endpoints
```

### Unit Testing

Test files in `tests/`:

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_get_status():
    response = client.get("/pipeline/status")
    assert response.status_code == 200
    assert "running" in response.json()

def test_start_pipeline():
    response = client.post("/pipeline/start", json={"scenario": "normal"})
    assert response.status_code == 200
    assert response.json()["success"] is True
```

**Run Tests**:
```bash
pytest tests/test_api.py -v
```

---

## Adding New Endpoints

### Step-by-Step Guide

1. **Define Schema** (`schemas.py`):
```python
class NewResponse(BaseModel):
    field1: str
    field2: int
```

2. **Create Route** (`routes/new.py`):
```python
from fastapi import APIRouter
from api.schemas import NewResponse

router = APIRouter()

@router.get("/endpoint", response_model=NewResponse)
async def new_endpoint():
    return NewResponse(field1="value", field2=42)
```

3. **Register Route** (`main.py`):
```python
from api.routes.new import router as new_router
app.include_router(new_router, prefix="/new")
```

4. **Test**:
```bash
curl http://localhost:8000/new/endpoint
```

---

**For general backend information, see [README.md](../README.md)**
