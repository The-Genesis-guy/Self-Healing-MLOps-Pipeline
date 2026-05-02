# 🏛️ Deep-Technical Architecture Manual

This document provides a granular explanation of the engineering principles, mathematical foundations, and infrastructure decisions behind the **Self-Healing MLOps Pipeline**.

---

## 1. The Core Control Loop (The "Self-Healing" Brain)

The system operates on an autonomous background loop (implemented in `api/runner.py`) that follows a strict state-machine pattern.

### 1.1 The Lifecycle of an Iteration
Every `LOOP_INTERVAL_SECONDS` (default: 10s), the system executes these steps:

1.  **Ingestion:** Data is pulled via the `Adapter` pattern. This ensures the core engine is decoupled from the data source (CSV, SQL, or API).
2.  **Sanity Check (The Guardrail):** The `DataValidator` scans the batch. If `is_valid` is False, the loop breaks immediately to prevent "garbage-in-garbage-out" poisoning.
3.  **Shadow Trial:** Before any new logic is executed, the system checks for a `shadow_model`. If one exists, it is tested against the `active_model` on the *newest* batch.
4.  **Drift Detection:** We calculate the **Population Stability Index (PSI)** for every feature.
5.  **Decision Matrix:** The `Healer` evaluates both current performance (F1) and data drift (PSI) to choose the most cost-effective action.
6.  **Action Execution:** The system performs `retrain`, `rollback`, or `none`.
7.  **Persistence:** The state is committed to `registry.db` and `history.db`.

---

## 2. Mathematical Foundation: Drift Detection

We use the **Population Stability Index (PSI)** to quantify how much the incoming data distribution has shifted from the training baseline.

### 2.1 The PSI Formula
For each feature, we divide the data into 10 deciles and calculate:
$$PSI = \sum (Actual\% - Expected\%) \times \ln\left(\frac{Actual\%}{Expected\%}\right)$$

### 2.2 Handling Sparse Data (Laplace Smoothing)
In production, a category or value range might appear in the baseline but be missing in the current batch (or vice-versa). A standard PSI would return `inf` or `NaN` due to division by zero. 

We implemented **Laplace Smoothing** in `core/drift.py`:
```python
# Smoothing factor ensures we never divide by zero
actual_pct = (actual_counts / total_actual) + 1e-6
expected_pct = (expected_counts / total_expected) + 1e-6
```
This ensures the pipeline remains stable even during extreme "Night Shift" scenarios where certain values vanish entirely.

---

## 3. Safety Gate Architecture

### 3.1 Shadow Deployment (Safe Promotion)
The system implements **Shadow Deployment** (Feature 4). When a new model is trained, it is marked as a candidate. 

**The Promotion Rule:**
A shadow model is *only* promoted if:
$$F1_{Shadow}(Batch_{N+1}) > F1_{Active}(Batch_{N+1})$$
This prevents "Overfitting to Drift"—the risk that a model trained on drifted data is only good for *that specific batch* but fails on subsequent ones.

### 3.2 Safe Mode (The Circuit Breaker)
To prevent infinite retraining loops that consume expensive compute resources, we implemented a **Circuit Breaker** (Feature 5). 
*   If retraining fails to produce a superior model **3 times in a row**, the system transitions to `health="critical"`.
*   It logs a `safe_mode` event and stops the background thread.
*   The system requires human intervention (via the Dashboard or API) to reset.

---

## 4. Module Deep-Dive

### 📂 `core/`
*   **`model.py`**: Encapsulates the `scikit-learn` Pipeline. It handles `SimpleImputer` for missing values and `OneHotEncoder` for categorical features within a single object, preventing **Data Leakage**.
*   **`drift.py`**: The mathematical engine. It uses `numpy` for vectorized PSI calculations.
*   **`healer.py`**: The decision engine. It uses a priority-based logic: **Rollback** (if performance is broken) > **Retrain** (if drift is high) > **Alert** (if drift is mild).
*   **`validator.py`**: The "Bouncer." Checks for null spikes (>10%) and constant columns (sensor failure).
*   **`registry.py`**: SQLite-backed version store. It serializes models using `joblib` and stores metadata/importance scores in a relational schema.

### 📂 `api/`
*   **`runner.py`**: The heartbeat. It manages a `threading.Thread` and uses `threading.Event` for clean shutdowns.
*   **`state.py`**: A thread-safe `PipelineState` object protected by `threading.Lock` to ensure the UI sees a consistent view of the pipeline even during retraining.
*   **`routes/`**: FastAPI endpoints that follow REST best practices.

---

## 5. Persistence Schema

### `models/registry.db`
Stores every model ever trained:
*   `version`: Auto-incrementing ID.
*   `path`: Location on disk.
*   `f1_score`: The validation score at training time.
*   `feature_importance`: A JSON-serialized dictionary of model weights.

### `models/history.db`
Stores the "Life Story" of the pipeline:
*   `iteration`: The loop count.
*   `model_version`: Which model was active.
*   `drift_score`: The maximum PSI detected.
*   `action`: What the system did (promote, discard, retrain, etc.).
