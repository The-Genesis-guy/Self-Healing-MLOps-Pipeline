# Self-Healing MLOps Pipeline: Architectural Analysis

## 1. Overall Architectural Health: ⭐⭐⭐⭐⭐ (5/5)
This project has successfully transitioned from a standard data science script into a **production-grade Software Engineering application**. 

The most impressive architectural feat is the implementation of the **Adapter Pattern (SOLID: Open-Closed Principle)**. The core algorithm is completely decoupled from the data. Any dataset can be plugged into this engine, and it will autonomously self-heal without touching the core logic.

---

## 2. The Core Engine (`/core/`)
This is the heart of the self-healing loop. It contains 6 distinct, single-responsibility modules:

*   **`model.py`:** Contains the `scikit-learn` Pipeline. It automatically handles `NaN` values and categorical strings. By embedding imputation and One-Hot Encoding directly into the mathematical pipeline, it completely prevents Data Leakage—a massive academic requirement.
*   **`drift.py`:** Contains the mathematics. It calculates the **Population Stability Index (PSI)** for every single feature, determining mathematically if the live data distribution has shifted from the baseline.
*   **`healer.py`:** The decision matrix. It reads the PSI scores and executes state logic: *Should I ignore this? Should I retrain? Should I roll back?*
*   **`retrainer.py`:** The guardian gate. If the Healer triggers it, it trains a new model. However, it *only* promotes the model if the new F1 score is strictly greater than the old F1 score.
*   **`registry.py`:** The SQLite database manager. It tracks every model version (e.g., `v1.pkl`, `v2.pkl`) and strictly enforces which version is actively deployed.
*   **`adapter.py`:** The interface contract. It forces any incoming dataset to provide standard methods like `get_current_data()` and `target_column()`.

---

## 3. The Translators (`/adapters/`)
This directory proves the system is domain-agnostic. 
*   **`fraud.py`:** Translates synthetic credit card fraud data.
*   **`churn.py`:** Translates customer churn data.
*   *(Planned: `paysim.py` which will handle the 6.3 Million row Kaggle dataset).*

---

## 4. The Command Center (`/api/`)
This is Layer 2: A high-performance **FastAPI** wrapper built around the core engine.

*   **`runner.py`:** Manages the background thread. It runs the infinite `Observe -> Compare -> Decide -> Act` loop asynchronously, ensuring it never blocks the API requests.
*   **`state.py`:** A thread-safe global dictionary. It tracks exactly what iteration the pipeline is on, the active model's F1 score, and the last action taken.
*   **`routes/`:** Exposes RESTful endpoints (`/pipeline/start`, `/models/active`, `/drift/check`) allowing a frontend UI or external service to control the engine.

---

## 5. Testing & Validation (`/tests/`)
The project utilizes a highly robust Pytest suite.
*   It executes exactly 18 distinct API and integration tests.
*   It tests critical edge cases, such as attempting to start the pipeline when it is already running, verifying rollback limits, and ensuring the target column (labels) never leaks into the drift checker.

---

## 6. Remaining Milestones to Project Completion

The backend architecture is currently **90% finished**. The following milestones remain:

1. **Phase 1: `data/streamer.py` (Kaggle PaySim) — COMPLETE ✅**
   *   Implemented the script to stream the 6.3M row Kaggle dataset in chunked memory buffers with zero-fraud protections.
2. **Phase 2: `adapters/paysim.py`**
   *   Writing the domain adapter that drops unique ID columns and invokes the streamer.
3. **Phase 3: `run_paysim_simulation.py`**
   *   Writing the terminal script to run the Kaggle simulation, proving the engine heals organic drift.
4. **Layer 3: The React Dashboard (UI)**
   *   Building the frontend interface that hooks into the `/api/` endpoints to visualize the PSI scores and retraining loops in real-time.
