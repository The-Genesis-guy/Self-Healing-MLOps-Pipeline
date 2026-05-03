# GUARDIAN: Self-Healing MLOps Pipeline

A production-grade, autonomous machine learning operations platform with real-time drift detection, automated model healing, and intelligent model promotion through shadow trials.

[![CI](https://github.com/The-Genesis-guy/Self-Healing-MLOps-Pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/The-Genesis-guy/Self-Healing-MLOps-Pipeline/actions/workflows/ci.yml)

## 🎯 Project Overview

GUARDIAN implements a **self-healing machine learning pipeline** that continuously monitors model performance and data drift, automatically retrains degraded models, and safely promotes improvements through A/B testing (shadow trials). The system operates 24/7 with zero human intervention while providing comprehensive visibility through an interactive React dashboard.

### Key Capabilities

- **Real-Time Monitoring**: Live performance and drift metrics with 2-second refresh intervals
- **Automatic Healing**: Autonomous retraining on detected drift without human intervention
- **Shadow Trials**: Safe model promotion through A/B testing before production release
- **Drift Detection**: Statistical PSI-based feature drift detection across all features
- **Multi-Model Registry**: Version history with automatic promotion and rollback
- **Explainability**: Feature importance visualization and actionable decision reasoning
- **Production Ready**: SQLite persistence, FastAPI backend, React 19 frontend, containerizable

---

## 🏗️ Architecture Layers

GUARDIAN is organized into three interconnected layers:

### **Layer 1: Frontend Dashboard** (`/dashboard`)
React 19 + TypeScript + Vite frontend providing real-time visualization and control.
- 6 feature-rich pages (Dashboard, Drift Radar, Models, Performance, Alerts, Logs)
- Live metrics and charts with Recharts
- Pipeline control panel (start/stop, adapter/scenario selection)
- Intelligent log aggregation for stable periods

**→ [Detailed Documentation](./docs/LAYER1_FRONTEND.md)**

### **Layer 2: API & Data Management** (`/api`)
FastAPI backend with RESTful endpoints and data schemas.
- `/pipeline/status` - Real-time pipeline state
- `/pipeline/history` - Persistent event log
- `/models` - Model registry and version management
- `/pipeline/drift` - Feature drift analysis
- Type-safe Pydantic schemas

**→ [Detailed Documentation](./docs/LAYER2_API.md)**

### **Layer 3: Core Pipeline Logic** (`/core`)
Autonomous decision-making and model training engine.
- **Healer**: Drift-based decision logic
- **Drift Calculator**: PSI-based feature drift detection
- **History Logger**: Event persistence and logging
- **Retrainer**: Automated model retraining with validation
- **Model Registry**: Version management and promotion
- **Validator**: Data quality guardrails

**→ [Detailed Documentation](./docs/LAYER3_CORE.md)**

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Git

### Installation & Running

#### 1. Clone & Setup Backend
```bash
git clone <repo>
cd Self-Healing-MLOps-Pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. Start Backend
```bash
# Terminal 1: Start FastAPI backend (recommended)
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Alternative: run as a module (convenience wrapper)
# This will start Uvicorn for you: `python -m api`
python3 -m api

# Backend runs on http://127.0.0.1:8000
```

#### 3. Start Pipeline Loop
```bash
# Terminal 2: Start pipeline loop
python3 pipeline.py
```

#### 4. Start Frontend
```bash
# Terminal 3: Start dashboard
cd dashboard
npm install && npm run dev

# Dashboard available at http://localhost:5173
```

---

## 📊 Core Features

### Real-Time Dashboard (Layer 1)

**6 Pages:**
1. **Dashboard** - Live metrics, drift summary, model status
2. **Drift Radar** - Detailed PSI scores for all features
3. **Model Registry** - Version history with promotion status
4. **Performance Chart** - F1-Score evolution with event markers
5. **Alerts** - Non-healthy event notifications
6. **Logs** - Aggregated event timeline (3+ stable periods grouped)

### Drift Detection (Layer 3)

**Decision Logic:**
```
1. F1 < MIN_THRESHOLD → ROLLBACK
2. Max(PSI) ≥ DRIFT_RETRAIN → RETRAIN
3. Max(PSI) ≥ DRIFT_ALERT → ALERT
4. Else → NONE (stable)
```

**PSI (Population Stability Index):**
- Normal: PSI < 0.10
- Mild: 0.10 ≤ PSI < 0.20
- High: 0.20 ≤ PSI < 0.30
- Severe: PSI ≥ 0.30 (triggers retraining)

### Model Healing (Layer 3)

**Shadow Trial Process:**
1. Detect drift → Trigger retraining
2. Train new model on latest data
3. A/B test: Compare new vs. active model F1 scores
4. Promote if new F1 > active F1, otherwise discard
5. Safety: Halt after 3 consecutive failed retrains

---

## 🔌 Key API Endpoints

```
GET /pipeline/status         → Current pipeline state
GET /pipeline/history        → Event log (2,120+ entries)
GET /models                  → Model registry with versions
POST /pipeline/start         → Start pipeline loop
POST /pipeline/stop          → Stop pipeline loop
```

Full API documentation at: [LAYER2_API.md](./docs/LAYER2_API.md)

---

## ⚙️ Configuration

Edit `config.py`:

```python
MIN_F1_THRESHOLD = 0.50          # Rollback threshold
DRIFT_RETRAIN_THRESHOLD = 0.30   # Severe drift threshold
DRIFT_ALERT_THRESHOLD = 0.10     # Mild drift threshold
LOOP_INTERVAL_SECONDS = 5        # Check interval
MAX_RETRAIN_ATTEMPTS = 3         # Safe mode trigger
```

---

## 📁 Project Structure

```
Self-Healing-MLOps-Pipeline/
├── README.md                    # This file
├── docs/
│   ├── LAYER1_FRONTEND.md      # Frontend documentation
│   ├── LAYER2_API.md           # API documentation
│   └── LAYER3_CORE.md          # Core logic documentation
├── dashboard/                   # React 19 frontend
├── api/                         # FastAPI backend
├── core/                        # Core ML logic
├── adapters/                    # Domain adapters
├── tests/                       # Test suite
├── config.py                    # Configuration
├── pipeline.py                  # CLI entry point
└── requirements.txt             # Dependencies
```

---

## 🧪 Testing

Automated checks now run in GitHub Actions on every push and pull request:
- Backend e2e tests in `tests/e2e/`
- Dashboard Playwright smoke tests in `dashboard/tests/e2e/`

```bash
pytest tests/ -v
# Coverage report: pytest tests/ --cov=core --cov=api
```

Test coverage:
- `test_healer.py` - Decision logic
- `test_drift.py` - PSI calculation
- `test_pipeline.py` - End-to-end flow
- `test_api.py` - Endpoints
- `test_registry.py` - Model management

---

## 📈 Data Flow Diagram

```
┌─────────────────────────────────────────┐
│      Data Ingestion (Adapter)           │
│  Load Current Batch + Baseline          │
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│    Core Pipeline Loop (runner.py)       │
│  1. Validate data quality               │
│  2. Check shadow trial status           │
│  3. Calculate drift (PSI)               │
│  4. Decide action (Healer)              │
│  5. Act (retrain/rollback/none)        │
│  6. Log event to history.db             │
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│    API & Persistence (FastAPI)          │
│  History logged, state updated          │
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│    Dashboard Visualization (React)      │
│  Real-time metrics, 2s refresh          │
└─────────────────────────────────────────┘
```

---

## 📚 Documentation

- **[README.md](README.md)** - Overview and quick start (you are here)
- **[LAYER1_FRONTEND.md](./docs/LAYER1_FRONTEND.md)** - Frontend architecture, components, styling
- **[LAYER2_API.md](./docs/LAYER2_API.md)** - API endpoints, schemas, request/response formats
- **[LAYER3_CORE.md](./docs/LAYER3_CORE.md)** - Core algorithms, decision logic, model management

Each layer document includes architecture, code structure, key algorithms, configuration, testing strategies, and performance notes.

---

## ✅ System Status

**Last Verified**: 2026-05-02 23:05 UTC

- ✅ Backend API: All endpoints responding
- ✅ Database: 2,120 history entries verified
- ✅ Frontend: All 6 pages operational
- ✅ Drift Detection: PSI calculation accurate
- ✅ Model Management: Registry operational
- ✅ Data Integrity: 100% verified
- ✅ Build Status: TypeScript passing

---

**For detailed information, see the layer documentation in `/docs` folder.**
