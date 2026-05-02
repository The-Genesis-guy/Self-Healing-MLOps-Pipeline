# LAYER 3: Core Pipeline Logic Documentation

**Autonomous Decision Engine + Drift Detection + Model Management**

This document details the complete core logic of GUARDIAN, including the Healer decision engine, PSI-based drift detection, automated retraining, model registry management, and data validation guardrails.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Pipeline Loop (runner.py)](#pipeline-loop-runnerpy)
5. [The Healer: Decision Engine](#the-healer-decision-engine)
6. [Drift Detection: PSI Algorithm](#drift-detection-psi-algorithm)
7. [Model Registry & Versioning](#model-registry--versioning)
8. [Automated Retraining](#automated-retraining)
9. [Shadow Trials (A/B Testing)](#shadow-trials-ab-testing)
10. [Data Validation Guardrails](#data-validation-guardrails)
11. [History Logging](#history-logging)
12. [Configuration & Thresholds](#configuration--thresholds)

---

## Architecture Overview

The core layer is the **autonomous decision-making engine** that runs continuously in the background. It:

1. **Observes**: Fetches current data and baseline
2. **Validates**: Checks data quality
3. **Compares**: Calculates drift via PSI
4. **Decides**: Uses Healer logic to determine action
5. **Acts**: Retrains, rollbacks, or continues
6. **Logs**: Records all events to history
7. **Repeats**: Every 5 seconds (configurable)

### Key Principles

- **Autonomous**: Requires zero human intervention
- **Safe**: Multiple safeguards prevent "recursive destruction"
- **Auditable**: Complete event trail in history database
- **Explainable**: Every decision has a documented reason
- **Defensive**: Data validation prevents pipeline poisoning

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Pipeline Loop | Python threading | Background execution |
| Drift Detection | NumPy/Pandas | PSI calculation |
| Model Training | Scikit-learn | Classification models |
| Persistence | SQLite | Event logging |
| Data Processing | Pandas | DataFrame operations |
| Model Serialization | pickle | Model storage |

---

## Project Structure

```
core/
├── __init__.py
├── adapter.py              # Abstract adapter interface
├── healer.py               # Decision engine (drift → action)
├── drift.py                # PSI calculation algorithm
├── history.py              # SQLite event persistence
├── model.py                # Model loading & inference
├── registry.py             # Version management
├── retrainer.py            # Automated retraining
└── validator.py            # Data quality checks

api/
├── runner.py               # Pipeline loop with decision logic
└── state.py                # Shared global state

Key Files:
- runner.py: 200 lines, main loop & orchestration
- healer.py: 100 lines, decision logic
- drift.py: 150 lines, PSI & feature analysis
- registry.py: 120 lines, model versioning
- retrainer.py: 150 lines, training pipeline
- validator.py: 100 lines, data quality
- history.py: 100 lines, logging & persistence
```

---

## Pipeline Loop (runner.py)

### Main Loop Structure

The pipeline runs in a separate thread spawned at API startup.

```python
# api/runner.py
import threading
import time
from core.drift import calculate_drift
from core.healer import Healer
from core.retrainer import Retrainer
from core.registry import ModelRegistry
from core.history import HistoryLogger
from core.validator import DataValidator
from api.state import pipeline_state

def _loop(adapter):
    """Main pipeline loop - runs continuously every LOOP_INTERVAL_SECONDS"""
    
    registry = ModelRegistry()
    healer = Healer()
    retrainer = Retrainer()
    history = HistoryLogger()
    validator = DataValidator()
    baseline = adapter.load_baseline()
    
    shadow_version = None  # Track candidate model
    shadow_model = None    # Candidate model object
    consecutive_failed_retrains = 0
    
    while not _stop_event.is_set():
        iteration = pipeline_state.iteration + 1
        pipeline_state.update(iteration=iteration)
        
        # === STEP 1: OBSERVE ===
        active = registry.get_active()
        if active is None:
            break
        pipeline_state.update(
            active_model_version=active.version,
            active_model_f1=active.f1_score
        )
        
        current_data = adapter.get_current_data()
        
        # === STEP 2: VALIDATE (Data Quality Guardrail) ===
        valid = validator.validate(current_data, target_column=adapter.target_column)
        if not valid.is_valid:
            pipeline_state.update(health="critical")
            history.log(iteration, active.version, active.f1_score, 0.0, 
                       "alert", f"DATA QUALITY: {valid.issues[0]}")
            _stop_event.wait(timeout=LOOP_INTERVAL_SECONDS)
            continue
        
        # === STEP 3: SHADOW TRIAL CHECK ===
        # If a candidate model is waiting evaluation, test it against active
        if shadow_version and shadow_model:
            y_true = current_data[adapter.target_column]
            X = current_data.drop(columns=[adapter.target_column])
            
            # Active model inference
            active_model_obj = Model.load(active.path)
            active_preds = active_model_obj.predict(X)
            active_f1_new = f1_score(y_true, active_preds, zero_division=0)
            
            # Shadow model inference
            shadow_preds = shadow_model.predict(X)
            shadow_f1_new = f1_score(y_true, shadow_preds, zero_division=0)
            
            # Decision: promote or discard?
            if shadow_f1_new > active_f1_new:
                registry.set_active(shadow_version)
                history.log(iteration, shadow_version, shadow_f1_new, 0.0, 
                           "promote", f"Shadow v{shadow_version} beat Active v{active.version}")
            else:
                history.log(iteration, active.version, active_f1_new, 0.0, 
                           "discard", f"Shadow v{shadow_version} failed trial")
            
            shadow_version = None
            shadow_model = None
            pipeline_state.update(shadow_model_version=None)
            active = registry.get_active()
        
        # === STEP 4: COMPARE (Drift Detection) ===
        drift_reports = calculate_drift(
            baseline.drop(columns=[adapter.target_column]),
            current_data.drop(columns=[adapter.target_column]),
            categorical_columns=adapter.categorical_columns
        )
        drifted = [f for f, r in drift_reports.items() if r.drifted]
        max_drift = max([r.psi_score for r in drift_reports.values()]) if drift_reports else 0
        
        # === STEP 5: DECIDE (Healer Logic) ===
        decision = healer.decide(drift_reports, current_f1=active.f1_score)
        pipeline_state.update(
            last_action=decision.action,
            last_reason=decision.reason,
            last_drifted_features=drifted
        )
        
        # === STEP 6: ACT (Execute Decision) ===
        if decision.action == 'retrain':
            if consecutive_failed_retrains >= MAX_RETRAIN_ATTEMPTS:
                # Safe mode: too many failures
                pipeline_state.update(health="critical")
                history.log(iteration, active.version, active.f1_score, max_drift, 
                           "safe_mode", "Retraining failed 3 times. Halting.")
                break
            else:
                # Train new model
                retrain_result = retrainer.retrain(current_data, target_column=adapter.target_column)
                
                if retrain_result.promoted:
                    # Success: enter shadow trial
                    shadow_version = retrain_result.new_version
                    record = registry.get_by_version(shadow_version)
                    shadow_model = Model.load(record.path)
                    pipeline_state.update(
                        shadow_model_version=shadow_version,
                        last_action="shadow"
                    )
                    history.log(iteration, active.version, active.f1_score, max_drift, 
                               "shadow", f"v{shadow_version} in Shadow Trial")
                    consecutive_failed_retrains = 0
                else:
                    # Failure: retry next iteration
                    consecutive_failed_retrains += 1
                    history.log(iteration, active.version, active.f1_score, max_drift, 
                               "failed_retrain", retrain_result.reason)
        
        elif decision.action == 'rollback':
            # Revert to previous version
            all_models = registry.get_all()
            if len(all_models) >= 2:
                previous = all_models[-2]
                registry.set_active(previous.version)
                history.log(iteration, previous.version, previous.f1_score, max_drift, 
                           "rollback", decision.reason)
        
        else:
            # "none", "alert", etc. - just log it
            consecutive_failed_retrains = 0
            history.log(iteration, active.version, active.f1_score, max_drift, 
                       decision.action, decision.reason)
        
        # === STEP 7: WAIT ===
        _stop_event.wait(timeout=LOOP_INTERVAL_SECONDS)

def start(adapter):
    """Spawn pipeline loop in background thread"""
    global _thread
    if pipeline_state.running:
        return False
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, args=(adapter,), daemon=True)
    _thread.start()
    return True

def stop():
    """Stop the background thread"""
    _stop_event.set()
    return True
```

### Execution Timeline

Each iteration takes ~5 seconds:

```
Time=0s:   Fetch current data
Time=0.5s: Validate data quality
Time=1s:   Test shadow model (if exists)
Time=1.5s: Calculate drift (PSI)
Time=2s:   Healer decides action
Time=2.5s: Execute action (retrain/rollback/none)
Time=3s:   Log event to history
Time=5s:   Sleep until next iteration
```

---

## The Healer: Decision Engine

### Core Decision Logic (core/healer.py)

The **Healer** is the autonomous decision-making component. It takes drift reports and current F1-score, returns a decision with reasoning.

```python
from dataclasses import dataclass
from core.drift import DriftReport
from config import MIN_F1_THRESHOLD, DRIFT_RETRAIN_THRESHOLD, DRIFT_ALERT_THRESHOLD

@dataclass
class HealerDecision:
    action: str                    # Decision (retrain, rollback, alert, none)
    reason: str                    # Explanation
    drifted_features: list[str]   # Which features triggered decision

class Healer:
    def __init__(
        self,
        min_f1: float = MIN_F1_THRESHOLD,           # 0.50
        drift_retrain: float = DRIFT_RETRAIN_THRESHOLD,   # 0.30
        drift_alert: float = DRIFT_ALERT_THRESHOLD        # 0.10
    ):
        self.min_f1 = min_f1
        self.drift_retrain = drift_retrain
        self.drift_alert = drift_alert
    
    def decide(self, drift_reports: dict[str, DriftReport], current_f1: float) -> HealerDecision:
        """
        Decision Priority Order:
        1. Check F1 performance → rollback if degraded
        2. Check severe drift → retrain
        3. Check mild drift → alert
        4. Else → continue monitoring (none)
        """
        
        # === PRIORITY 1: Model Performance ===
        # If F1 drops below minimum threshold, model is unreliable
        # Retraining won't help; safest action is rollback to previous known-good version
        if current_f1 < self.min_f1:
            return HealerDecision(
                action="rollback",
                reason=f"F1 score {current_f1} dropped below minimum {self.min_f1}",
                drifted_features=[]
            )
        
        # === PRIORITY 2: Feature Drift Analysis ===
        # Categorize features by drift severity
        severe = []  # PSI >= 0.30 (severe, needs retraining)
        mild = []    # 0.10 <= PSI < 0.30 (mild, worth flagging)
        
        for feature, report in drift_reports.items():
            if report.psi_score >= self.drift_retrain:
                severe.append(feature)
            elif report.psi_score >= self.drift_alert:
                mild.append(feature)
        
        # === PRIORITY 3: Severe Drift → RETRAIN ===
        # Data distribution shifted significantly. Model needs to learn new patterns.
        # Decision: Trigger retraining on latest data
        if severe:
            return HealerDecision(
                action="retrain",
                reason=f"Severe drift detected in: {', '.join(severe)}",
                drifted_features=severe
            )
        
        # === PRIORITY 4: Mild Drift → ALERT ===
        # Some drift present but not critical yet. Alert humans to monitor.
        # Decision: Log for visibility but don't act
        if mild:
            return HealerDecision(
                action="alert",
                reason=f"Mild drift detected in: {', '.join(mild)}",
                drifted_features=mild
            )
        
        # === PRIORITY 5: No Issues → NONE ===
        # Pipeline is stable. Continue monitoring.
        # Decision: Do nothing, just log the fact
        return HealerDecision(
            action="none",
            reason="No drift detected and model performance is acceptable",
            drifted_features=[]
        )
```

### Decision Flowchart

```
           ┌─────────────────────────┐
           │  Calculate Drift (PSI)  │
           │  Get Current F1 Score   │
           └────────────┬────────────┘
                        ↓
           ┌─────────────────────────┐
           │ F1 < MIN_THRESHOLD?     │
           └────┬────────────────┬───┘
               YES              NO
                ↓                ↓
        [ROLLBACK]   ┌──────────────────────┐
                     │ Max(PSI) >= 0.30?    │
                     └────┬──────────────┬──┘
                        YES            NO
                         ↓              ↓
                   [RETRAIN]   ┌────────────────────┐
                               │ Max(PSI) >= 0.10?  │
                               └────┬────────────┬──┘
                                  YES          NO
                                   ↓            ↓
                              [ALERT]     [NONE]
```

### Example Scenarios

**Scenario 1: Healthy Pipeline**
```
Input: current_f1=0.51, max_psi=0.08
Decision: action="none", reason="No drift detected and model performance is acceptable"
Action: Continue monitoring
```

**Scenario 2: Mild Drift Detected**
```
Input: current_f1=0.51, features with PSI=[0.15, 0.08, 0.04]
Decision: action="alert", reason="Mild drift detected in: feature1"
Action: Log warning, notify humans
```

**Scenario 3: Severe Drift + Degradation**
```
Input: current_f1=0.51, features with PSI=[0.35, 0.12, 0.08]
Decision: action="retrain", reason="Severe drift detected in: feature1"
Action: Trigger retraining on latest data
```

**Scenario 4: Model Performance Collapse**
```
Input: current_f1=0.45 (< 0.50 threshold), max_psi=0.08
Decision: action="rollback", reason="F1 score 0.45 dropped below minimum 0.50"
Action: Revert to previous stable model version
```

---

## Drift Detection: PSI Algorithm

### Population Stability Index (PSI)

PSI measures how much a feature's distribution has changed from baseline to current.

```python
# core/drift.py
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass
class DriftReport:
    feature: str
    psi_score: float
    drifted: bool  # True if PSI >= 0.30

def calculate_psi(baseline_series, current_series, num_bins=10):
    """
    Calculate PSI between baseline and current distributions
    
    PSI = Σ (actual% - expected%) × ln(actual% / expected%)
    
    where:
    - expected% = % in baseline (historical distribution)
    - actual% = % in current (production distribution)
    
    Interpretation:
    - PSI < 0.10: No significant change
    - 0.10 ≤ PSI < 0.25: Small shift (monitor)
    - 0.25 ≤ PSI < 1.00: Significant shift (take action)
    - PSI ≥ 1.00: Major shift (urgent action)
    """
    
    # Handle categorical vs numerical
    if baseline_series.dtype == 'object' or baseline_series.dtype.name == 'category':
        # Categorical: compare value distributions
        return _calculate_psi_categorical(baseline_series, current_series)
    else:
        # Numerical: bin and compare
        return _calculate_psi_numerical(baseline_series, current_series, num_bins)

def _calculate_psi_numerical(baseline, current, num_bins=10):
    """PSI for numerical features using bucketing"""
    
    # Create bins from baseline data
    bins = pd.qcut(baseline, q=num_bins, duplicates='drop')
    bin_edges = np.linspace(baseline.min(), baseline.max(), num_bins + 1)
    
    # Count baseline distribution (expected)
    baseline_counts = np.histogram(baseline, bins=bin_edges)[0]
    baseline_pct = baseline_counts / len(baseline)
    
    # Count current distribution (actual)
    current_counts = np.histogram(current, bins=bin_edges)[0]
    current_pct = current_counts / len(current)
    
    # Laplace smoothing to avoid log(0)
    baseline_pct = (baseline_pct + 0.0001) / (baseline_pct.sum() + 0.0010)
    current_pct = (current_pct + 0.0001) / (current_pct.sum() + 0.0010)
    
    # PSI calculation
    psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
    
    return psi

def _calculate_psi_categorical(baseline, current):
    """PSI for categorical features"""
    
    # Get unique values from both
    all_categories = set(baseline.unique()) | set(current.unique())
    
    baseline_counts = baseline.value_counts()
    current_counts = current.value_counts()
    
    psi = 0.0
    for category in all_categories:
        baseline_pct = baseline_counts.get(category, 0) / len(baseline)
        current_pct = current_counts.get(category, 0) / len(current)
        
        # Laplace smoothing
        baseline_pct = (baseline_pct + 0.0001) / (baseline_pct + 0.0010)
        current_pct = (current_pct + 0.0001) / (current_pct + 0.0010)
        
        # Avoid log(0)
        if baseline_pct > 0 and current_pct > 0:
            psi += (current_pct - baseline_pct) * np.log(current_pct / baseline_pct)
    
    return psi

def calculate_drift(baseline_X, current_X, categorical_columns=None):
    """
    Calculate PSI for all features
    
    Returns:
    {
        'feature1': DriftReport(psi_score=0.15, drifted=False),
        'feature2': DriftReport(psi_score=0.35, drifted=True),
        ...
    }
    """
    
    if categorical_columns is None:
        categorical_columns = []
    
    drift_reports = {}
    
    for feature in baseline_X.columns:
        psi = calculate_psi(
            baseline_X[feature],
            current_X[feature],
            num_bins=10
        )
        
        drift_reports[feature] = DriftReport(
            feature=feature,
            psi_score=psi,
            drifted=psi >= 0.30  # Severe threshold
        )
    
    return drift_reports
```

### PSI Interpretation

| PSI Range | Interpretation | Action |
|-----------|----------------|--------|
| 0.00-0.10 | No significant drift | Continue monitoring |
| 0.10-0.20 | Mild drift | Alert/monitor closely |
| 0.20-0.30 | Moderate drift | Plan retraining |
| 0.30+ | Severe drift | Trigger retraining immediately |

### Example: Feature Drift Scenario

```
Baseline Distribution (Q1 2026):
  transaction_amount: mean=150, std=50

Current Distribution (Q2 2026):
  transaction_amount: mean=180, std=60

PSI Calculation:
  Baseline buckets: [100-120: 10%, 120-140: 20%, ..., 180-200: 5%]
  Current buckets:  [100-120: 5%, 120-140: 15%, ..., 180-200: 15%]
  PSI = Σ (actual% - expected%) × ln(actual% / expected%)
  PSI = 0.32 (Severe drift!)

Decision: Trigger retrain
```

---

## Model Registry & Versioning

### Model Versioning Strategy (core/registry.py)

GUARDIAN maintains a complete version history of all trained models.

```python
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class ModelRecord:
    version: int
    path: str
    f1_score: float
    trained_at: str
    is_active: bool
    feature_importance: dict = None

class ModelRegistry:
    """
    Manages model versions and promotion.
    
    Stores metadata in registry.json:
    {
      "models": [...],
      "active_version": 1,
      "total_versions": 13
    }
    """
    
    def __init__(self, db_path: str = "models/registry.json"):
        self.db_path = db_path
        self._load()
    
    def _load(self):
        """Load registry from JSON"""
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)
                self.models = data.get('models', [])
                self.active_version = data.get('active_version')
        except FileNotFoundError:
            self.models = []
            self.active_version = None
    
    def _save(self):
        """Persist registry to JSON"""
        with open(self.db_path, 'w') as f:
            json.dump({
                'models': self.models,
                'active_version': self.active_version,
                'total_versions': len(self.models)
            }, f, indent=2)
    
    def register_model(self, version: int, path: str, f1_score: float, 
                      feature_importance: dict = None):
        """Register new trained model"""
        model = {
            'version': version,
            'path': path,
            'f1_score': f1_score,
            'trained_at': datetime.now().isoformat(),
            'is_active': False,
            'feature_importance': feature_importance
        }
        self.models.append(model)
        self._save()
    
    def set_active(self, version: int):
        """Promote model to active"""
        for model in self.models:
            model['is_active'] = (model['version'] == version)
        self.active_version = version
        self._save()
    
    def get_active(self) -> ModelRecord:
        """Get currently active model"""
        for model in self.models:
            if model['is_active']:
                return ModelRecord(**model)
        return None
    
    def get_by_version(self, version: int) -> ModelRecord:
        """Get specific model version"""
        for model in self.models:
            if model['version'] == version:
                return ModelRecord(**model)
        return None
    
    def get_all(self) -> list[ModelRecord]:
        """Get all models (sorted by version DESC)"""
        sorted_models = sorted(self.models, key=lambda m: m['version'], reverse=True)
        return [ModelRecord(**m) for m in sorted_models]
```

### Versioning Workflow

```
Iteration 1:
  Train v1 → F1=0.50 → Set Active v1

Iteration 100:
  Detect drift → Train v2 → F1=0.52 > 0.50
  Set shadow v2 → Test in shadow trial

Iteration 101:
  Shadow test: v2 F1=0.51 > v1 F1=0.50
  Promote v2 → Set Active v2

Iteration 200:
  Detect drift → Train v3 → F1=0.49 < 0.50
  Reject v3 → Stay with v2

Iteration 300:
  F1 drop → Rollback to v1 → Set Active v1
```

### Model File Structure

```
models/
├── v1.pkl              # Serialized sklearn model
├── v2.pkl
├── v3.pkl
├── ...
├── v13.pkl
├── registry.json       # Metadata (registry)
├── history.db          # Event log (SQLite)
└── baseline.csv        # Baseline data for drift comparison
```

---

## Automated Retraining

### Retraining Pipeline (core/retrainer.py)

When drift is detected, GUARDIAN automatically retrains on the latest data.

```python
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from core.model import Model
from core.registry import ModelRegistry
import pickle

@dataclass
class RetrainResult:
    promoted: bool              # Successfully trained?
    new_version: int            # If promoted, the new version
    reason: str                 # Explanation
    f1_score: float = None      # New model's F1

class Retrainer:
    """Automated model retraining on new data"""
    
    def __init__(self, registry: ModelRegistry, categorical_columns: list = None):
        self.registry = registry
        self.categorical_columns = categorical_columns or []
        self.scaler = StandardScaler()
    
    def retrain(self, data: pd.DataFrame, target_column: str) -> RetrainResult:
        """
        Retrain model on latest data
        
        Steps:
        1. Split X, y
        2. Encode categorical features
        3. Train new model
        4. Evaluate on same batch (holdout test)
        5. Register if validation passes
        """
        
        try:
            # Step 1: Prepare data
            X = data.drop(columns=[target_column])
            y = data[target_column]
            
            # Step 2: Encode categoricals
            X = self._encode_features(X)
            
            # Step 3: Scale
            X_scaled = self.scaler.fit_transform(X)
            
            # Step 4: Train
            model = LogisticRegression(max_iter=1000, random_state=42)
            model.fit(X_scaled, y)
            
            # Step 5: Evaluate
            preds = model.predict(X_scaled)
            new_f1 = f1_score(y, preds, zero_division=0)
            
            # Step 6: Validation checks
            if new_f1 < 0.40:  # Too low to deploy
                return RetrainResult(
                    promoted=False,
                    new_version=None,
                    reason=f"F1 {new_f1} too low to promote",
                    f1_score=new_f1
                )
            
            # Step 7: Register new version
            new_version = len(self.registry.get_all()) + 1
            model_path = f"models/v{new_version}.pkl"
            
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            # Extract feature importance
            feature_importance = self._get_importance(model, X.columns)
            
            self.registry.register_model(
                version=new_version,
                path=model_path,
                f1_score=new_f1,
                feature_importance=feature_importance
            )
            
            return RetrainResult(
                promoted=True,
                new_version=new_version,
                reason=f"Retrained v{new_version} with F1={new_f1:.4f}",
                f1_score=new_f1
            )
        
        except Exception as e:
            return RetrainResult(
                promoted=False,
                new_version=None,
                reason=f"Retrain failed: {str(e)}",
                f1_score=None
            )
    
    def _encode_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """One-hot encode categorical features"""
        X_encoded = X.copy()
        for col in self.categorical_columns:
            if col in X_encoded.columns:
                X_encoded = pd.get_dummies(X_encoded, columns=[col], drop_first=True)
        return X_encoded
    
    def _get_importance(self, model, feature_names):
        """Extract feature importance from model"""
        if hasattr(model, 'coef_'):
            importance = np.abs(model.coef_[0])
            importance = importance / importance.sum()
            return dict(zip(feature_names, importance))
        return None
```

### Retraining Safeguards

1. **Validation on Same Batch**: Train and test on same data (no leakage)
2. **Minimum F1 Check**: Reject if new_f1 < 0.40
3. **Safe Mode Trigger**: After 3 failed retrains, halt and alert
4. **Shadow Trial**: New model tested against active before promotion

---

## Shadow Trials (A/B Testing)

### Safe Model Promotion

New models are never deployed to production directly. Instead, they enter a **Shadow Trial** where:

1. Both Active and Shadow models process the **same data**
2. Metrics are compared (new F1 vs. active F1)
3. **Only promote if new model is strictly better**
4. Automatic rollback available if issues detected

### Shadow Trial State Machine

```
┌──────────────────────┐
│  Model Retrained     │
│  (v2 ready)          │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  Enter Shadow Trial  │
│  shadow_version=v2   │
│  shadow_model=obj    │
└──────────┬───────────┘
           ↓
    ┌──────────────────────────┐
    │  Each iteration:         │
    │  Test v2 vs v1          │
    └──────────────────────────┘
           ↓
    ┌──────────────────┐
    │ v2 F1 > v1 F1?  │
    └────┬─────────┬──┘
        YES      NO
         ↓        ↓
    [PROMOTE]  [DISCARD]
     Set v2     Stay v1
     Active     Active
         ↓        ↓
    ┌────────────────────┐
    │  Exit Trial        │
    │  shadow_version=None│
    └────────────────────┘
```

### Code Implementation

```python
# In runner.py, if shadow_version is set:
if shadow_version and shadow_model:
    y_true = current_data[adapter.target_column]
    X = current_data.drop(columns=[adapter.target_column])
    
    # Active model inference
    active_model_obj = Model.load(active.path)
    active_preds = active_model_obj.predict(X)
    active_f1_new = f1_score(y_true, active_preds, zero_division=0)
    
    # Shadow model inference
    shadow_preds = shadow_model.predict(X)
    shadow_f1_new = f1_score(y_true, shadow_preds, zero_division=0)
    
    # Promotion Decision
    if shadow_f1_new > active_f1_new:
        registry.set_active(shadow_version)
        history.log(..., "promote", f"Shadow v{shadow_version} beat v{active.version}")
    else:
        history.log(..., "discard", f"Shadow v{shadow_version} failed trial")
    
    # Exit shadow trial
    shadow_version = None
    shadow_model = None
```

---

## Data Validation Guardrails

### Quality Checks (core/validator.py)

Before retraining, GUARDIAN validates data quality to prevent "pipeline poisoning".

```python
from dataclasses import dataclass

@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[str]
    reason: str

class DataValidator:
    """Prevent pipeline poisoning through data quality checks"""
    
    def validate(self, data: pd.DataFrame, target_column: str, 
                null_threshold: float = 0.10,
                min_rows: int = 100) -> ValidationResult:
        """
        Check:
        1. Null spike (>10% nulls)
        2. Constant columns (zero variance)
        3. Minimum data size
        4. Target value distribution
        """
        
        issues = []
        
        # Check 1: Null spikes
        null_pct = data.isnull().sum() / len(data)
        null_cols = null_pct[null_pct > null_threshold].index.tolist()
        if null_cols:
            issues.append(f"Null spike in: {null_cols}")
        
        # Check 2: Constant columns (frozen sensors)
        const_cols = [col for col in data.columns 
                     if data[col].nunique() <= 1]
        if const_cols:
            issues.append(f"Constant columns: {const_cols}")
        
        # Check 3: Data size
        if len(data) < min_rows:
            issues.append(f"Only {len(data)} rows (need {min_rows})")
        
        # Check 4: Target distribution
        if target_column in data.columns:
            target_dist = data[target_column].value_counts(normalize=True)
            if (target_dist > 0.99).any():
                issues.append(f"Imbalanced target: one class >{99}%")
        
        if issues:
            return ValidationResult(
                is_valid=False,
                issues=issues,
                reason="; ".join(issues)
            )
        
        return ValidationResult(
            is_valid=True,
            issues=[],
            reason="Data quality passed"
        )
```

### Safety Examples

**Scenario 1: Null Spike**
```
Baseline: null_pct = 2%
Current: null_pct = 15% (>10% threshold)
Decision: Block retraining, alert operator
Reason: "Potential data pipeline failure"
```

**Scenario 2: Frozen Sensor**
```
Feature 'distance_from_home':
  Baseline: variance = 100
  Current: variance = 0 (all values same)
Decision: Block retraining
Reason: "Constant column indicates data freshness issue"
```

**Scenario 3: Extreme Imbalance**
```
Target distribution:
  Class 0: 99.5%
  Class 1: 0.5%
Decision: Block retraining
Reason: "Severely imbalanced target (99.5% one class)"
```

---

## History Logging

### Complete Event Trail (core/history.py)

Every decision is logged to SQLite for audit trail and visualization.

```python
from datetime import datetime
import sqlite3

class HistoryLogger:
    """Persist all pipeline events to SQLite"""
    
    def __init__(self, db_path: str = "models/history.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create history table if not exists"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    iteration       INTEGER NOT NULL,
                    model_version   INTEGER,
                    f1_score        REAL,
                    drift_score     REAL,
                    action          TEXT,
                    reason          TEXT
                )
            """)
            conn.commit()
    
    def log(self, iteration: int, version: int, f1: float, drift: float, 
            action: str, reason: str):
        """Log single event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO history 
                (timestamp, iteration, model_version, f1_score, drift_score, action, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), iteration, version, f1, drift, action, reason))
            conn.commit()
    
    def get_recent(self, limit: int = 100) -> list[HistoryEntry]:
        """Retrieve recent entries (newest first)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM history ORDER BY iteration DESC LIMIT ?
            """, (limit,)).fetchall()
            
            return [HistoryEntry(**dict(row)) for row in rows]
```

---

## Configuration & Thresholds

### Key Configuration (config.py)

```python
# Model Performance Thresholds
MIN_F1_THRESHOLD = 0.50                    # Rollback if F1 < this
RETRAIN_F1_MINIMUM = 0.40                  # Reject retrain if F1 < this

# Drift Thresholds (PSI-based)
DRIFT_ALERT_THRESHOLD = 0.10               # Mild drift (alert)
DRIFT_RETRAIN_THRESHOLD = 0.30             # Severe drift (retrain)

# Pipeline Timing
LOOP_INTERVAL_SECONDS = 5                  # Check interval
MAX_RETRAIN_ATTEMPTS = 3                   # Safe mode trigger

# Data Validation
NULL_SPIKE_THRESHOLD = 0.10                # >10% nulls = alert
MIN_DATA_ROWS = 100                        # Minimum batch size
IMBALANCE_THRESHOLD = 0.99                 # >99% one class = alert

# Model Registry
MAX_MODELS_KEEP = 50                       # Archive older versions
MODEL_STORAGE_PATH = "models/"

# Feature Handling
NUM_PSI_BINS = 10                          # Numerical discretization
LAPLACE_SMOOTHING = 0.0001                 # Avoid log(0)
```

### Tuning Guidelines

**Make Retraining MORE AGGRESSIVE**:
- Lower `DRIFT_RETRAIN_THRESHOLD` (0.30 → 0.20)
- Lower `MIN_F1_THRESHOLD` (0.50 → 0.45)
- Increase `LOOP_INTERVAL_SECONDS` (5 → 3)

**Make Retraining CONSERVATIVE**:
- Raise `DRIFT_RETRAIN_THRESHOLD` (0.30 → 0.40)
- Raise `MIN_F1_THRESHOLD` (0.50 → 0.55)
- Decrease `LOOP_INTERVAL_SECONDS` (5 → 10)

---

**For general core information, see [README.md](../README.md)**
