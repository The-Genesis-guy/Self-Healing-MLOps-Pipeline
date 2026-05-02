# 🤖 Self-Healing MLOps Pipeline

**The Future of Autonomous Machine Learning Operations**

A production-grade, closed-loop MLOps system that detects data drift, evaluates performance, and heals itself via autonomous retraining and shadow deployment safety gates. This project uses the **6.3 Million row PaySim dataset** to simulate a high-fidelity fraud detection environment.

---

## 🌟 The 5 Master-Level Engineering Features

This is not a simple script; it is a hardened infrastructure that solves the most common failures in real-world ML:

### 🛡️ 1. Guardian Gate (Shadow Deployment)
Never deploy a model blindly again. When a new model is trained, it enters a **Shadow Trial**. Both the Active and Shadow models process the *same* live data. The system only promotes the Shadow model if it achieves a higher F1-score on the **real, incoming batch**.

### 🩺 2. The Data Bouncer (Quality Guardrails)
Prevent "Pipeline Poisoning." The `DataValidator` module acts as a sanity check. It blocks retraining if it detects:
*   **Null Spikes:** >10% missing values (indicates a sensor/pipe failure).
*   **Frozen Sensors:** Constant columns where data used to be dynamic.
*   **Domain Violations:** Values that defy business logic (e.g., negative transaction amounts).

### 📊 3. PSI-Driven Drift Detection
We use the **Population Stability Index (PSI)** to mathematically quantify distribution shifts. Our implementation uses **Laplace Smoothing** to remain stable even when categories vanish or appear for the first time in production.

### 🧠 4. Explainable AI (XAI)
Every model in our `registry.db` includes its **Feature Importance** scores. These are exposed via the API and stored per-version, allowing you to see exactly how the model's "logic" evolves as it adapts to new data.

### 🧯 5. Safe Mode (Circuit Breaker)
To prevent "Recursive Destruction" (training models on corrupted data or unresolvable drift), the system features a **Circuit Breaker**. After 3 consecutive failed retraining attempts, the system halts, logs a `safe_mode` event, and signals for human intervention.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
*   Python 3.10+
*   FastAPI / Uvicorn
*   Scikit-learn / Pandas / Numpy

### 2. Clone and Install
```bash
git clone https://github.com/The-Genesis-guy/Self-Healing-MLOps-Pipeline.git
cd Self-Healing-MLOps-Pipeline
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Data Download
Download the [PaySim Dataset from Kaggle](https://www.kaggle.com/datasets/ealaxi/paysim1) and place it in the root folder as:
`PS_20174392719_1491204439457_log.csv`

---

## 🚀 Usage Guide

### The Master Simulation (CLI)
To watch the pipeline autonomously process the 6.3M rows and heal itself as chronological drift occurs:
```bash
python run_paysim_simulation.py
```

### The API Server
To launch the backend for the Dashboard and interact with the REST API:
```bash
# Run from the root directory
uvicorn api.main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` for the interactive Swagger documentation.

---

## 📐 Deep-Technical Architecture
For a granular explanation of the math, threading, and state-management, please see:
👉 [**ARCHITECTURE.md**](ARCHITECTURE.md)

---

## 📂 Detailed Project Structure
*   **`core/`**: The algorithmic heart (Drift, Healer, Model, Validator).
*   **`adapters/`**: Domain-specific logic (PaySim, Fraud). Decouples data from the engine.
*   **`api/`**: The FastAPI infrastructure and background runner logic.
*   **`data/`**: The memory-safe chronological streaming engine.
*   **`models/`**: Persistent SQLite stores for models (`registry.db`) and logs (`history.db`).
*   **`tests/`**: 44 automated unit and integration tests.
*   **`config.py`**: Centralized thresholds for PSI, F1, and Retraining caps.

---

## 🧪 Testing
The system maintains 100% reliability with a full test suite.
```bash
pytest tests/ -v
```
**Results:** 44 Passed ✅ | 0 Failed ❌
