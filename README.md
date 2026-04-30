# Self-Healing MLOps Pipeline

A closed-loop, autonomous ML pipeline that observes incoming data, detects drift, decides on a course of action, and automatically retrains or rolls back models without human intervention.

## Architecture

This project is structured in three distinct layers to cleanly separate the algorithm, the infrastructure, and the user interface.

### Layer 1: The Brain (Core Algorithm)
A pure Python implementation of the self-healing algorithm. It operates entirely locally and has no dependencies on web servers or external services.

**The Control Loop:**
1. **OBSERVE** — Check the active model and its current F1 score.
2. **COMPARE** — Calculate Population Stability Index (PSI) to detect drift between the baseline and incoming live data.
3. **DECIDE** — Trigger an action based on severity: `none`, `alert`, `retrain`, or `rollback`.
4. **ACT** — Execute the decision (e.g., retrain the model and promote it *only* if the new F1 score is higher).
5. **VERIFY** — Confirm the new active state.

👉 [Read the full Layer 1 Deep-Dive Documentation](layer1_complete.md)

### Layer 2: The API (Infrastructure)
A FastAPI wrapper that brings the Brain online. It runs the pipeline loop safely in a background thread while exposing a REST API to observe and control the system.

- **Start/Stop Controls:** `/pipeline/start`, `/pipeline/stop`
- **State Observation:** `/pipeline/status`, `/models`, `/models/active`
- **On-Demand Drift:** `/drift/check`

👉 [Read the full Layer 2 API Integration Guide](layer2_complete.md)

### Layer 3: The Dashboard (React)
*(Coming Soon)* A Vite/React frontend to visualize live drift alerts, track model version history, and monitor pipeline health.

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

# 4. Generate initial training data and train the baseline model (v1)
python generate_data.py
python -c "
import pandas as pd
from core.registry import ModelRegistry
from core.retrainer import Retrainer
retrainer = Retrainer(registry=ModelRegistry(), categorical_columns=['merchant_category', 'is_foreign'])
retrainer.retrain(pd.read_csv('data_training.csv'), target_column='is_fraud')
"
```

---

## Running the API (Layer 2)

Start the FastAPI server:

```bash
uvicorn api.main:app --reload --port 8000
```

Once running, you can:
- View Interactive Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Start the pipeline: `POST http://localhost:8000/pipeline/start?scenario=normal`
- Check status: `GET http://localhost:8000/pipeline/status`

---

## Test Suite

The project includes 38 passing unit and integration tests covering drift calculation (PSI), healer decision logic, registry CRUD operations, rollback execution, and all API endpoints.

```bash
pytest tests/ -v
```

---

## Key Features
* **Population Stability Index (PSI):** Surgically identifies exactly which features have drifted.
* **Guardian Gate Promotion:** Retrained models are only promoted to active status if they genuinely outperform the previous baseline.
* **Retrain Capping:** Prevents infinite loop compute waste on unwinnable drift scenarios (e.g., extreme data shifts where the signal is entirely lost).
* **Immutable Registry:** Full audit trail tracking version history, F1 scores, timestamps, and `.pkl` file paths.
