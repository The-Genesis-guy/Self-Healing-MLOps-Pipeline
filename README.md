# Self-Healing MLOps Pipeline

A closed-loop, autonomous ML pipeline that observes incoming data, detects drift, decides on a course of action, and automatically retrains or rolls back models without human intervention.

**Current Status:** Layers 1 & 2 Complete ✅ | Layer 1.5 In Progress 🚧  
**Test Coverage:** 38/38 core tests passing | 18/18 API tests passing 
**Model Registry:** 16 versions trained, v1 active (F1=0.5085)  
**Next:** Real dataset support (`data/streamer.py` built, moving to PaySim adapter)

## Architecture

This project is structured in three distinct layers to cleanly separate the algorithm, the infrastructure, and the user interface.

### Layer 1: The Brain (Core Algorithm) ✅
**Status:** Complete — 20 tests passing

A pure Python implementation of the self-healing algorithm. It operates entirely locally and has no dependencies on web servers or external services.

**The Control Loop:**
1. **OBSERVE** — Check the active model and its current F1 score.
2. **COMPARE** — Calculate Population Stability Index (PSI) to detect drift between the baseline and incoming live data.
3. **DECIDE** — Trigger an action based on severity: `none`, `alert`, `retrain`, or `rollback`.
4. **ACT** — Execute the decision (e.g., retrain the model and promote it *only* if the new F1 score is higher).
5. **VERIFY** — Confirm the new active state.

**Key Features:**
- Domain-agnostic core engine
- PSI-based drift detection
- Guardian gate promotion (only promote if F1 improves)
- Retrain capping (prevents infinite loops on unwinnable drift)
- Full audit trail with SQLite registry

👉 [Read the full Layer 1 Deep-Dive Documentation](layer1_complete.md)

### Layer 2: The API (Infrastructure) ✅
**Status:** Complete — 18 tests passing

A FastAPI wrapper that brings the Brain online. It runs the pipeline loop safely in a background thread while exposing a REST API to observe and control the system.

**Endpoints:**
- **Start/Stop Controls:** `POST /pipeline/start`, `POST /pipeline/stop`
- **State Observation:** `GET /pipeline/status`, `GET /models`, `GET /models/active`
- **On-Demand Drift:** `GET /drift/check?scenario=foreign`
- **Manual Control:** `POST /models/{version}/activate`

**Key Features:**
- Thread-safe background processing
- CORS support for React frontend
- Interactive Swagger docs at `/docs`
- Pydantic validation for type safety
- Full observability via status endpoint

👉 [Read the full Layer 2 API Integration Guide](layer2_complete.md)

### Layer 3: The Dashboard (React) ⚠️
**Status:** Not yet implemented

A Vite/React frontend to visualize live drift alerts, track model version history, and monitor pipeline health.

**Planned Features:**
- Real-time drift visualization
- Model version timeline
- Manual drift simulation controls
- Active model switcher
- Alert notifications

---

## Project Structure

```
Self-Healing-MLOps-Pipeline/
├── core/                      # Layer 1: Domain-agnostic engine
│   ├── model.py               # Train, predict, save, load
│   ├── drift.py               # PSI calculation
│   ├── healer.py              # Decision engine
│   ├── retrainer.py           # Retrain + promotion logic
│   └── registry.py            # SQLite model version store
│
├── adapters/                  # Domain-specific knowledge (swappable)
│   └── fraud.py               # Fraud detection features + drift scenarios
│
├── api/                       # Layer 2: HTTP wrapper
│   ├── main.py                # FastAPI app
│   ├── state.py               # Thread-safe shared state
│   ├── runner.py              # Background loop
│   ├── schemas.py             # Pydantic models
│   └── routes/                # API endpoints
│       ├── pipeline.py        # Start/stop/status
│       ├── models.py          # List/active/activate
│       └── drift.py           # On-demand drift check
│
├── tests/                     # 38 tests, all passing
│   ├── test_drift.py          # PSI calculations
│   ├── test_healer.py         # Decision logic
│   ├── test_registry.py       # Model store CRUD
│   ├── test_pipeline.py       # Integration tests
│   └── test_api.py            # API endpoints
│
├── data/                      # Data streaming layer
│   └── streamer.py            # Sequential chunked CSV reader
│
├── models/                    # Model artifacts + registry
│   ├── registry.db            # SQLite database
│   └── v*.pkl                 # Trained model files
│
├── config.py                  # All tunable thresholds
├── pipeline.py                # CLI runner (Layer 1)
├── generate_data.py           # Synthetic fraud data generator
├── simulate_drift.py          # Drift inspector CLI tool
├── data_training.csv          # 1000 rows baseline data
├── requirements.txt           # Python dependencies
├── layer1_complete.md         # Layer 1 documentation
└── layer2_complete.md         # Layer 2 documentation
```

---

## Current Production State

**Model Registry:** 16 versions trained

```
Version    F1 Score     Status
─────────────────────────────
v1         0.5085       ✅ ACTIVE
v2         0.5085       
v3         0.4889       
v4         0.5417       ← highest performer
v5-v7      0.48-0.51    
v8-v16     0.25-0.39    ← degraded performance
```

**Key Observations:**
- v1 remains active after 16 retraining attempts
- v4 achieved the highest F1 (0.5417) but wasn't promoted
- Later versions show degraded performance, indicating unwinnable drift scenarios
- Retrain capping prevents infinite compute waste on these scenarios

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/The-Genesis-guy/Self-Healing-MLOps-Pipeline.git
cd Self-Healing-MLOps-Pipeline

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate initial training data
python generate_data.py

# 5. Train the baseline model (v1)
python -c "
import pandas as pd
from core.registry import ModelRegistry
from core.retrainer import Retrainer
registry = ModelRegistry()
retrainer = Retrainer(registry=registry, categorical_columns=['merchant_category', 'is_foreign'])
df = pd.read_csv('data_training.csv')
result = retrainer.retrain(df, target_column='is_fraud')
print(f'✅ v{result.new_version} trained | F1={result.new_f1} | Fraud rate: {df[\"is_fraud\"].mean():.1%}')
"
```

**Expected output:**
```
Generated 1000 rows
Fraud rate: 11.7%
Model saved to models/v1.pkl
✅ v1 trained | F1=0.5085 | Fraud rate: 11.7%
```

---

## Quick Start

### Run Layer 1 (CLI)
```bash
# Activate virtual environment
source venv/bin/activate

# Run pipeline for 3 iterations with normal scenario
python -c "from pipeline import run_pipeline; run_pipeline(scenario='normal', max_iterations=3)"

# Inspect drift scores without running full loop
python simulate_drift.py foreign
```

### Run Layer 2 (API)
```bash
# Start the FastAPI server
uvicorn api.main:app --reload --port 8000
```

Once running, you can:
- View Interactive Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Start the pipeline: `POST http://localhost:8000/pipeline/start?scenario=normal`
- Check status: `GET http://localhost:8000/pipeline/status`
- Get all models: `GET http://localhost:8000/models`
- Check drift: `GET http://localhost:8000/drift/check?scenario=foreign`

---

## Test Suite

The project includes **38 passing tests** covering all critical functionality:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_drift.py` | 4 | PSI calculations, drift detection |
| `test_healer.py` | 5 | Decision logic (none/alert/retrain/rollback) |
| `test_registry.py` | 7 | Model versioning, activation, rollback |
| `test_pipeline.py` | 4 | Full integration cycles |
| `test_api.py` | 18 | All API endpoints, lifecycle management |

```bash
# Run all tests
pytest tests/ -v

# Run specific layer
pytest tests/test_drift.py tests/test_healer.py tests/test_registry.py tests/test_pipeline.py -v  # Layer 1
pytest tests/test_api.py -v  # Layer 2
```

**Result:** 38 passed in ~4.5s ✅

---

## Key Features

### Core Algorithm
* **Population Stability Index (PSI):** Surgically identifies exactly which features have drifted
* **Guardian Gate Promotion:** Retrained models are only promoted if they genuinely outperform the previous baseline
* **Retrain Capping:** Prevents infinite loop compute waste on unwinnable drift scenarios (MAX_RETRAIN_ATTEMPTS=3)
* **Baseline Evolution:** Updates reference point after successful retrains to prevent infinite loops
* **Immutable Registry:** Full audit trail tracking version history, F1 scores, timestamps, and `.pkl` file paths

### Domain Agnostic Design
* **Swappable Adapters:** Core engine knows nothing about fraud detection — domain knowledge lives in `adapters/`
* **Apply to Any Domain:** Create `adapters/churn.py` or `adapters/credit_risk.py` — core stays identical
* **Configurable Thresholds:** All tunable parameters in `config.py`

### Production Ready
* **Thread-Safe API:** Background processing with proper locking
* **Comprehensive Tests:** 38 tests covering unit, integration, and API levels
* **Proper Logging:** Structured logging (not print statements)
* **Class Imbalance Handling:** Balanced weights + custom threshold + F1 metric
