# Self-Healing MLOps Pipeline

A closed-loop, autonomous ML pipeline that observes incoming streaming data, detects drift mathematically, decides on a course of action, and automatically retrains or rolls back models without human intervention.

**Current Status:** Layers 1 & 2 Complete ✅ | Layer 3 (React) In Progress 🚧  
**Test Coverage:** 38/38 core & API tests passing 
**Simulation Engine:** Supports infinite chronological stream processing via chunked memory buffers.

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
- Domain-agnostic core engine (Adapter pattern + Dependency Injection)
- `scikit-learn` Pipeline integration to prevent data leakage during autonomous training
- PSI-based drift detection on continuous incoming chunks
- Guardian gate promotion (only promote if F1 improves on the new drifted distribution)
- Retrain capping (prevents infinite loops on unwinnable drift)

👉 [Read the full Layer 1 Deep-Dive](docs/layer1_core_engine.md)

### Layer 2: The API (Infrastructure) ✅
**Status:** Complete — 18 tests passing

A FastAPI wrapper that brings the Brain online. It runs the pipeline loop safely in a background thread while exposing a REST API to observe and control the system.

**Endpoints:**
- **Start/Stop Controls:** `POST /pipeline/start`, `POST /pipeline/stop`
- **State Observation:** `GET /pipeline/status`, `GET /models`, `GET /models/active`
- **On-Demand Drift:** `GET /drift/check?scenario=foreign`

**Key Features:**
- Thread-safe background processing
- CORS support for React frontend
- Interactive Swagger docs at `/docs`

👉 [Read the full Layer 2 API Integration Guide](docs/layer2_api.md)

### Layer 3: The Dashboard (React) ⚠️
**Status:** In Development

A Vite/React frontend to visualize live drift alerts, track model version history, and monitor pipeline health.

---

## Project Structure

```
Self-Healing-MLOps-Pipeline/
├── core/                      # Layer 1: Domain-agnostic engine
│   ├── model.py               # Scikit-learn Pipeline (Imputation, OHE, RandomForest)
│   ├── drift.py               # PSI calculation
│   ├── healer.py              # Decision engine
│   ├── retrainer.py           # Retrain + promotion logic
│   └── registry.py            # SQLite model version store
│
├── adapters/                  # Domain-specific knowledge (swappable)
│   ├── paysim.py              # Kaggle PaySim preprocessing
│   ├── fraud.py               # Synthetic fraud rules
│   └── churn.py               # Churn rules
│
├── data/                      # Data streaming layer
│   └── streamer.py            # Sequential chunked CSV reader (Memory-safe)
│
├── api/                       # Layer 2: HTTP wrapper
│   ├── main.py                # FastAPI app
│   ├── state.py               # Thread-safe shared state
│   ├── runner.py              # Background loop
│   └── routes/                # API endpoints
│
├── docs/                      # Extensive Documentation
│   ├── project_idea_and_architecture.md
│   ├── paysim_streaming_implementation.md
│   ├── layer1_core_engine.md
│   ├── layer2_api.md
│   └── future_roadmap.md
│
├── tests/                     # 38 tests, all passing
├── models/                    # SQLite registry and .pkl files
├── config.py                  # All tunable thresholds
├── pipeline.py                # CLI runner (Layer 1)
├── run_paysim_simulation.py   # Master Simulation Script
└── requirements.txt           # Python dependencies
```

---

## Installation & Kaggle Simulation

This project simulates a real-world MLOps environment by chronologically streaming the massive **6.3 Million Row Kaggle PaySim Dataset** through the self-healing algorithm.

```bash
# 1. Clone the repository
git clone https://github.com/The-Genesis-guy/Self-Healing-MLOps-Pipeline.git
cd Self-Healing-MLOps-Pipeline

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 4. Download the Dataset
You must download the [PaySim Mobile Money Fraud Dataset from Kaggle](https://www.kaggle.com/datasets/ealaxi/paysim1). 
Extract the `.csv` file into the root of this project folder and rename it to `PS_20174392719_1491204439457_log.csv`.

---

## Quick Start: The Grand Finale

Once the Kaggle dataset is in your root folder, you can run the master simulation script:

```bash
python run_paysim_simulation.py
```

### What happens when you run this?
1. The `DataStreamer` instantly grabs the first 100,000 rows (without loading the 500MB file into memory).
2. The `PaysimAdapter` strips out high-cardinality ID columns that would normally crash `scikit-learn`'s One-Hot Encoder.
3. The core engine mathematically trains the baseline `v1.pkl` model.
4. The pipeline enters an infinite loop, streaming the next 100,000 rows iteratively.
5. As the `step` column naturally drifts over chronological time, the **Healer detects the drift**, retrains a new model, evaluates it against the baseline, and promotes it autonomously if it scores higher.

Sit back and watch your terminal autonomously heal a Machine Learning model.

---

## Test Suite

The project includes **38 passing tests** covering all critical functionality across Layers 1 and 2.

```bash
# Run all tests
pytest tests/ -v
```

**Result:** 38 passed ✅
