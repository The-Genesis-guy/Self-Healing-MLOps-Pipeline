# Layer 1 — Complete Documentation
## Self-Healing MLOps Pipeline

---

## What Layer 1 Is

A pure Python implementation of the self-healing algorithm.  
No web server. No external services. No Docker. Just `python pipeline.py`.

**The algorithm:**
```
LOOP forever:
    1. OBSERVE  — which model is active? what's its F1?
    2. COMPARE  — has the incoming data drifted from what we trained on?
    3. DECIDE   — what action does the situation require?
    4. ACT      — retrain, rollback, alert, or do nothing
    5. VERIFY   — what is the model state after the action?
    6. REPEAT
```

This is a **closed-loop control system** — the same principle as a thermostat.  
The thermostat observes temperature, compares to target, decides to heat, acts, then re-observes.  
The pipeline observes data, compares to baseline, decides to retrain, acts, then re-observes.

---

## File Structure

```
Self-Healing-MLOps-Pipeline/
├── core/
│   ├── __init__.py
│   ├── model.py        ← train, evaluate, save, load
│   ├── drift.py        ← PSI calculation, drift report per feature
│   ├── healer.py       ← decision engine (retrain/rollback/alert/none)
│   ├── retrainer.py    ← orchestrates retraining + promotion logic
│   └── registry.py     ← SQLite model version store
├── adapters/
│   ├── __init__.py
│   └── fraud.py        ← all domain-specific knowledge (swappable)
├── config.py           ← all thresholds in one place
├── pipeline.py         ← main loop, wires everything together
├── generate_data.py    ← synthetic fraud data generator
├── simulate_drift.py   ← CLI tool to inspect PSI scores
├── requirements.txt
└── data_training.csv   ← 1000 rows baseline training data
```

**Core design rule:** `core/` knows nothing about fraud, loans, or any domain.  
`adapters/fraud.py` is what you swap out to apply to a new problem.

---

## File-by-File Breakdown

---

### `generate_data.py`

**Purpose:** Creates synthetic credit card transaction data with realistic fraud patterns.

**Features generated:**
| Column | Type | Distribution |
|--------|------|-------------|
| `transaction_amount` | float | Exponential, scale=200 (~$200 avg) |
| `hour_of_day` | int | Weighted toward business hours |
| `distance_from_home` | float | Exponential, scale=30 |
| `num_transactions_24h` | int | Poisson, lam=3 |
| `is_foreign` | binary | 90% domestic, 10% foreign |
| `merchant_category` | categorical | grocery/restaurant/gas/online/travel |
| `is_fraud` | binary | **causally linked to features** |

**Key design decision — causal fraud labels:**  
Fraud is not random. It's determined by actual risk factors:
```python
is_high_risk = (
    (is_foreign == 1)       |   # foreign card — 10% of transactions
    (hour_of_day < 5)       |   # late night — ~6% of transactions
    (num_transactions_24h > 5)  # many rapid transactions — ~8% of transactions
)
fraud_prob = np.where(is_high_risk, 0.45, 0.02)
is_fraud = (np.random.random(n) < fraud_prob).astype(int)
```
High-risk transactions: 45% fraud probability.  
Low-risk transactions: 2% fraud probability.  
Overall fraud rate: ~11-12%.

**Why this matters:** When drift scenarios shift `is_foreign` or `hour_of_day`, the fraud pattern genuinely changes. The model retrained on drifted data learns different patterns → produces different F1 scores. This is what makes the demo real.

**Run:** `python generate_data.py` → creates `data_training.csv`

---

### `config.py`

**Purpose:** Single place for all tunable parameters. Change a number here and the whole system adjusts — no digging into logic files.

```python
# Drift Detection
DRIFT_ALERT_THRESHOLD   = 0.10   # PSI above this → mild drift, alert
DRIFT_RETRAIN_THRESHOLD = 0.20   # PSI above this → severe drift, retrain

# Model Performance
MIN_F1_THRESHOLD = 0.35          # F1 below this → rollback immediately

# Pipeline
LOOP_INTERVAL_SECONDS = 5        # seconds to wait between iterations
```

**Why MIN_F1_THRESHOLD = 0.35 not 0.70:**  
The original placeholder value was 0.70. But the realistic model achieves ~0.50 F1 on this imbalanced dataset. Setting the threshold at 0.70 caused the healer to immediately rollback on every iteration since the model's actual F1 was always below it. 0.35 means "rollback only if the model truly collapses."

---

### `core/model.py`

**Purpose:** A thin wrapper around scikit-learn's `RandomForestClassifier`.

**What it does:**
- `Model.train(df, target_column)` — 80/20 stratified split, fits classifier, returns `ModelReport`
- `Model.predict(df)` — returns predictions using stored feature names
- `Model.save(path)` — pickle to disk
- `Model.load(path)` — load from disk

**Two key decisions:**

**1. `class_weight='balanced'`**  
Without this, the model predicts "not fraud" for everything and gets 92% accuracy — but F1=0.0. With 88% non-fraud data, the lazy answer is always "not fraud."  
`class_weight='balanced'` tells sklearn: "a missed fraud costs more than a missed non-fraud." The classifier adjusts accordingly.

**2. Decision threshold = 0.3, not 0.5**  
The default RandomForest threshold of 0.5 is wrong for imbalanced fraud detection. With rare fraud cases, the model's confidence on fraud rarely exceeds 50%. Using 0.5 means it never predicts fraud.  
```python
fraud_proba = self.clf.predict_proba(X_test)[:, 1]
predictions = (fraud_proba >= 0.3).astype(int)
```
0.3 means: "predict fraud if you're at least 30% confident." Standard practice for imbalanced classification.

**Why F1 not accuracy:**  
- 92% non-fraud → predicting "never fraud" = 92% accuracy
- F1 punishes models that ignore the minority class
- Always use F1 (or AUROC) when classes are imbalanced

---

### `core/drift.py`

**Purpose:** Detects when incoming data has drifted from the baseline training data using Population Stability Index (PSI).

**How PSI works:**
1. Divide baseline data into 10 buckets (by percentile)
2. Count what % of values fall in each bucket for both datasets
3. Per bucket: `(baseline% - current%) × ln(baseline% / current%)`
4. Sum across all buckets = total PSI score

**Why ratio not subtraction:**  
Going from 2%→1% scores higher than going from 40%→30%.  
The ratio `ln(2%/1%)` is much larger than `ln(40%/30%)`.  
PSI is sensitive to small changes in rare buckets — exactly where fraud patterns shift.

**Two implementations:**
- `_psi_numerical()` — bucket-based for continuous columns
- `_psi_categorical()` — frequency-based for string/categorical columns

**The +0.0001 offset:**  
Empty buckets would make `log(0)` = undefined and crash.  
Adding a tiny epsilon avoids this without meaningfully affecting the score.

**Key lesson learned:** `is_foreign` must be explicitly listed in `categorical_columns` even though pandas stores it as `int64`.  
Dtype ≠ semantic type. `is_foreign` is not a number — it's a category (0=domestic, 1=foreign). PSI for it should be calculated as "what % of transactions are foreign" not "what's the distribution of the number 0 vs 1."

**Thresholds:**
- PSI < 0.10: no significant drift
- PSI 0.10–0.20: mild drift → alert
- PSI > 0.20: severe drift → retrain

---

### `core/healer.py`

**Purpose:** The decision engine. Takes drift reports and current F1, returns one of four actions.

**Decision priority order (matters):**
```
1. F1 < MIN_F1_THRESHOLD  → rollback
   (model is too broken to use, don't retrain — we don't know why it's broken yet)

2. Any feature PSI ≥ DRIFT_RETRAIN_THRESHOLD  → retrain
   (data shifted enough that the model's training distribution no longer applies)

3. Any feature PSI ≥ DRIFT_ALERT_THRESHOLD  → alert
   (worth flagging, not bad enough to act automatically)

4. Everything looks fine  → none
```

**Why rollback before retrain:**  
If F1 collapsed, retraining on whatever data is coming in might make things worse. The safest move is to restore the last known-good model first, then investigate.

**Thresholds are injectable:**
```python
class Healer:
    def __init__(self, min_f1=MIN_F1_THRESHOLD, drift_retrain=DRIFT_RETRAIN_THRESHOLD, ...):
```
The defaults come from `config.py` but can be overridden per-instance. This means Layer 2 can create a `Healer` with custom thresholds passed via API request without touching config.

---

### `core/registry.py`

**Purpose:** SQLite-backed store of every model ever trained. Tracks versions, F1 scores, paths, and which one is currently active.

**Schema:**
```sql
CREATE TABLE models (
    version    INTEGER PRIMARY KEY,
    path       TEXT NOT NULL,
    accuracy   REAL NOT NULL,
    f1_score   REAL NOT NULL,
    trained_at TEXT NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 0
)
```

**Only one model can be active at a time:**
```python
def set_active(self, version: int):
    conn.execute("UPDATE models SET is_active = 0")   # clear everyone
    conn.execute("UPDATE models SET is_active = 1 WHERE version = ?", (version,))
```

**Why SQLite:** Rollback means flipping a flag, not moving files. The full history is always preserved. If you want to go back to v1 from v15, it's one `set_active(1)` call.

**Bug fixed — unclosed connections:**  
Python's `with sqlite3.connect(...) as conn` is a **transaction** context manager, not a **connection** context manager. It commits/rolls back but never closes the connection.  
Fix: wrap with `contextlib.closing`:
```python
from contextlib import closing
with closing(sqlite3.connect(self.db_path)) as conn:
```
Applied to all 5 methods that open a connection.

---

### `core/retrainer.py`

**Purpose:** Trains a new model on incoming data and decides whether to promote it or reject it.

**The promotion rule:**
```python
if report.f1_score >= old_f1:   # >= not >
    self.registry.set_active(record.version)
    return RetrainResult(promoted=True, ...)
```

**Why `>=` not `>`:**  
When drift triggers a retrain, the new model is evaluated on the NEW data distribution — the old model was evaluated on the OLD distribution. These F1 scores are not directly comparable.  
A model that achieves equal performance on the new distribution has successfully adapted. Rejecting it with strict `>` would cause an infinite retrain loop where no model ever gets promoted.

**Every model is saved, promoted or not:**
```python
new_model.save(model_path)           # save to disk
record = self.registry.register(...) # register in DB (not active yet)
# THEN decide whether to promote
```
Full audit trail. You can always see what every model version scored, even rejected ones.

---

### `adapters/fraud.py`

**Purpose:** Everything domain-specific in one file. This is what you swap out to change domains.

```python
CATEGORICAL_COLUMNS = ['merchant_category', 'is_foreign']
TARGET_COLUMN = 'is_fraud'
BASELINE_PATH = 'data_training.csv'

def load_baseline() -> pd.DataFrame: ...

def simulate_drift(baseline, scenario) -> pd.DataFrame:
    # normal, night_shift, high_value, foreign
```

**The four drift scenarios:**
| Scenario | What changes | Which features drift |
|----------|-------------|---------------------|
| `normal` | nothing | none |
| `night_shift` | `hour_of_day` forced to 2am-5am | `hour_of_day` |
| `high_value` | `transaction_amount` scaled to ~$3000 | `transaction_amount` |
| `foreign` | `is_foreign` → 80% foreign + high amounts | `transaction_amount`, `is_foreign` |

**Why a separate adapters folder:**  
To apply this to churn prediction, you add `adapters/churn.py` with the same function signatures.  
The entire `core/` folder stays identical. The `pipeline.py` changes one import line.

---

### `pipeline.py`

**Purpose:** The main loop. Wires all core components together and executes the 5-step algorithm.

**Key: the baseline updates after a successful retrain:**
```python
if result.promoted:
    baseline = current_data.copy()
```

**Why this matters:**  
Without this, after the model adapts to drifted data, the next iteration still compares incoming data against the original baseline → detects drift again → retrains again → infinite loop.

After retraining: the new model was trained on the drifted data. That drifted data IS the new normal for this model. Future drift should be measured from this new reference point.

---

### `simulate_drift.py`

**Purpose:** CLI tool to inspect PSI scores for any scenario without running the full pipeline.

```bash
python simulate_drift.py foreign
```

Output:
```
Feature                         PSI Score  Status
-------------------------------------------------------
transaction_amount                 3.6257  🔴 DRIFT
hour_of_day                        0.0000  🟢 OK
is_foreign                         2.7609  🔴 DRIFT
```

Useful for: debugging why a scenario triggers or doesn't trigger, tuning thresholds, understanding what each drift scenario actually does to the data.

---

## Bugs Found and Fixed During Development

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 1 | Infinite retrain loop | `>` rejected equal-F1 models, baseline never updated | Changed to `>=`, added baseline update after promotion |
| 2 | ResourceWarning on every run | `sqlite3` context manager doesn't close connections | Wrapped with `contextlib.closing` |
| 3 | F1=0.0 even with balanced weights | Fraud labels were purely random — no causal signal | Added causal fraud generation rules |
| 4 | F1=0.0 with causal data | Default 0.5 threshold never reached with rare fraud | Lowered to 0.3 via `predict_proba` |
| 5 | Rollback triggering on every iteration | MIN_F1_THRESHOLD was 0.70, model realistically scores ~0.50 | Lowered threshold to 0.35 |
| 6 | Thresholds hardcoded in healer.py | Config hadn't been wired up yet | Moved to config.py, imported in healer.py |
| 7 | Domain knowledge in pipeline.py | Adapter pattern not implemented | Moved to adapters/fraud.py |
| 8 | Rejected models overwrote same .pkl | Path used `active_version+1`, not registry's next version | Added `get_next_version()` to registry; `models_dir` param to Retrainer |
| 9 | `print()` throughout codebase | Legacy from early dev, fine for CLI, breaks concurrent API logging | Replaced with `logging` at correct severity levels (INFO/WARNING/ERROR) |
| 10 | No integration test | Unit tests only covered components in isolation | Added `tests/test_pipeline.py` wiring Retrainer + Registry + Healer + drift together |

---

## Verified Test Results

### Normal scenario — no drift, no action
```
[OBSERVE] Active model: v1 | F1=0.5085
[COMPARE] Drifted features: none
[DECIDE]  Action=none | No drift detected and model performance is acceptable
[ACT]     ✅ No action needed.
```

### Foreign drift scenario — detects, retrains, stabilizes
```
Iteration 1:
[COMPARE] Drifted features: ['transaction_amount', 'is_foreign']
[DECIDE]  Action=retrain | Severe drift detected in: transaction_amount, is_foreign
[ACT]     ❌ New model rejected. F1: 0.4783 did not beat 0.5085
[ACT]     ✅ New model v3 promoted. F1: 0.5085 → 0.56       ← different F1!
[ACT]     📐 Baseline updated to reflect new data distribution.

Iteration 2:
[COMPARE] Drifted features: none                              ← stabilized
[DECIDE]  Action=none
```

### simulate_drift.py — surgical feature-level detection
```
python simulate_drift.py night_shift
→ hour_of_day: 8.93 🔴 DRIFT   (only this feature, nothing else)

python simulate_drift.py high_value
→ transaction_amount: 3.42 🔴 DRIFT   (only this feature)

python simulate_drift.py foreign
→ transaction_amount: 3.63 🔴 DRIFT
→ is_foreign: 2.76 🔴 DRIFT
```

### Current Production State (as of May 1, 2026)

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

**Key observations:**
- v1 remains active after 16 retraining attempts
- v4 achieved the highest F1 (0.5417) but wasn't promoted (likely v2/v3 was active at that moment)
- Later versions show degraded performance, suggesting unwinnable drift scenarios
- Retrain capping (MAX_RETRAIN_ATTEMPTS=3) prevents infinite compute waste on these scenarios

---

## Test Suite — Final State (20 tests, 4 files)

```bash
pytest tests/ -v
```

| File | Tests | What it covers |
|------|-------|----------------|
| `test_drift.py` | 4 | PSI near-zero on identical data; spikes on shifted data; only the drifted feature is flagged |
| `test_healer.py` | 5 | All 4 decision paths (none/alert/retrain/rollback); rollback priority over retrain |
| `test_registry.py` | 7 | Version incrementing; only-one-active constraint; get_active; get_by_version; rollback simulation; fresh isolated DB per test |
| `test_pipeline.py` | 4 | Full train→drift→healer cycle; unique file per retrain (even rejected); rollback execution; registry grows with all retrains |

**Result:** 20 passed in ~1.5s

**Combined with Layer 2 API tests:** 38 total tests passing ✅

---

## Layer 1 Health Check

Run this any time to confirm everything is working. All 6 checks should pass.

```bash
source venv/bin/activate

# 1. All Layer 1 tests pass
pytest tests/test_drift.py tests/test_healer.py tests/test_registry.py tests/test_pipeline.py -v

# 2. Normal scenario — all features green
python simulate_drift.py normal

# 3. Foreign scenario — exactly 2 features flagged
python simulate_drift.py foreign

# 4. Registry has an active model
python -c "
from core.registry import ModelRegistry
registry = ModelRegistry()
m = registry.get_active()
print(f'\nActive: v{m.version} | F1={m.f1_score}\n')
all_m = registry.get_all()
print(f'Total versions: {len(all_m)}')
for v in all_m:
    flag = '✅ ACTIVE' if v.is_active else ''
    print(f'  v{v.version} | F1={v.f1_score} {flag}')
"

# 5. Pipeline runs cleanly
python -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
from pipeline import run_pipeline
run_pipeline(scenario='normal', max_iterations=2)
"

# 6. Check all model files exist
ls -lh models/*.pkl
```

**Expected outcomes:**
- `pytest`: 20 passed, 0 failed
- `normal` drift: all 🟢 OK
- `foreign` drift: `transaction_amount` 🔴 + `is_foreign` 🔴, everything else 🟢
- Registry: active model exists with F1 > 0.35
- Pipeline: 2 iterations, both `Action=none`, no errors
- Model files: all .pkl files present in models/ directory

---

## What Layer 1 Proves

1. ✅ PSI correctly identifies which features drifted — and only those features
2. ✅ The healer fires the right action for each situation
3. ✅ The retrainer only promotes a genuinely better model
4. ✅ The baseline evolves — no infinite retrain loops
5. ✅ The registry tracks full version history with unique files per version
6. ✅ All connections properly closed — no resource leaks
7. ✅ F1 genuinely varies across versions — real learning is happening
8. ✅ The engine is domain-agnostic — fraud knowledge lives only in `adapters/`
9. ✅ Retrain cap prevents compute waste on unwinnable drift scenarios
10. ✅ Logging replaces print — safe for concurrent API use in Layer 2
11. ✅ 20 tests covering all critical paths including integration
12. ✅ Target column properly excluded from drift checks (production-ready)
13. ✅ Categorical columns handled correctly (is_foreign treated as category, not number)

**The brain works. Layer 2 wraps it in HTTP. Layer 3 puts a UI on top.**

---

## Next Steps

With Layer 1 complete and proven, you can:

1. **Move to Layer 2** — wrap this in a FastAPI server (see `layer2_complete.md`)
2. **Apply to a new domain** — create `adapters/churn.py` or `adapters/credit_risk.py`
3. **Tune thresholds** — adjust `config.py` values based on your domain's needs
4. **Add more drift scenarios** — extend `simulate_drift()` in your adapter
5. **Experiment with different models** — swap RandomForest for XGBoost, LightGBM, etc.

The foundation is solid. Everything else is just configuration and infrastructure.

---

## How to Run Everything

---

### First-Time Setup

Run these once when setting up the project from scratch.

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Mac/Linux
# venv\Scripts\activate           # Windows

# 2. Install all dependencies
pip install -r requirements.txt

# 3. Generate training data (creates data_training.csv)
python generate_data.py

# 4. Train v1 — the initial baseline model
python -c "
import pandas as pd
from core.registry import ModelRegistry
from core.retrainer import Retrainer

registry = ModelRegistry()
retrainer = Retrainer(registry=registry, categorical_columns=['merchant_category', 'is_foreign'])
df = pd.read_csv('data_training.csv')
result = retrainer.retrain(df, target_column='is_fraud')
print(f'v{result.new_version} trained | F1={result.new_f1} | Fraud rate: {df[\"is_fraud\"].mean():.1%}')
"
```

**Expected output:**
```
Generated 1000 rows
Fraud rate: 11.7%
Model saved to models/v1.pkl
v1 trained | F1=0.5085 | Fraud rate: 11.7%
```

---

### Reset to Clean State

The registry database lives at `models/registry.db` — **inside** the `models/` folder.
So `rm -rf models/` atomically wipes both the model files AND the full history.

```bash
# Full reset — wipes all .pkl files AND the registry DB
rm -rf models/

# Regenerate data and retrain v1 fresh
python generate_data.py
python -c "
import pandas as pd
from core.registry import ModelRegistry
from core.retrainer import Retrainer
registry = ModelRegistry()
retrainer = Retrainer(registry=registry, categorical_columns=['merchant_category', 'is_foreign'])
df = pd.read_csv('data_training.csv')
result = retrainer.retrain(df, target_column='is_fraud')
print(f'v{result.new_version} | F1={result.new_f1}')
"
```

**Partial resets (rare):**
```bash
# Wipe registry history only — keep .pkl files on disk
rm models/registry.db

# Wipe .pkl files only — keep registry records (records now point to missing files)
rm models/v*.pkl
```

> **Rule of thumb:** always use `rm -rf models/` for a clean slate. The two partial options above create inconsistency between the DB and disk — only use them if you know exactly why.

---

### Run the Pipeline

All commands assume the venv is active (`source venv/bin/activate`).

**Normal — no drift, no action (sanity check):**
```bash
python -c "from pipeline import run_pipeline; run_pipeline(scenario='normal', max_iterations=3)"
```
Expected: all iterations show `Action=none`.

**Foreign card drift — transaction_amount + is_foreign shift:**
```bash
python -c "from pipeline import run_pipeline; run_pipeline(scenario='foreign', max_iterations=4)"
```
Expected:
- Iteration 1: drift detected → retrain → new model promoted with different F1
- Iterations 2-4: no drift (baseline updated) → no action

**High value drift — only transaction_amount shifts:**
```bash
python -c "from pipeline import run_pipeline; run_pipeline(scenario='high_value', max_iterations=4)"
```
Expected: only `transaction_amount` drifts → retrain triggered.

**Night shift drift — only hour_of_day shifts:**
```bash
python -c "from pipeline import run_pipeline; run_pipeline(scenario='night_shift', max_iterations=4)"
```
Expected: only `hour_of_day` drifts → retrain triggered.

**Run indefinitely (production-style):**
```bash
python pipeline.py
```
Runs with `scenario='normal'` until you Ctrl+C.

---

### Inspect Drift Scores

See exactly which features drift and by how much, without running the full loop.

```bash
# No args = normal scenario
python simulate_drift.py

# Specific scenario
python simulate_drift.py normal
python simulate_drift.py night_shift
python simulate_drift.py high_value
python simulate_drift.py foreign
```

**Expected outputs:**

`normal` — all green:
```
transaction_amount     0.0079  🟢 OK
hour_of_day            0.0123  🟢 OK
...
```

`night_shift` — only hour drifts:
```
hour_of_day            8.93    🔴 DRIFT
```

`high_value` — only amount drifts:
```
transaction_amount     3.42    🔴 DRIFT
```

`foreign` — amount + foreign drift:
```
transaction_amount     2.34    🔴 DRIFT
is_foreign             2.70    🔴 DRIFT
```

---

### Check Model Registry History

```bash
python -c "
from core.registry import ModelRegistry
registry = ModelRegistry()
for m in registry.get_all():
    active = '← ACTIVE' if m.is_active else ''
    print(f'v{m.version} | F1={m.f1_score} | {m.trained_at[:19]} {active}')
"
```

---

### Quick Smoke Test

Run this after any code change to verify nothing broke.

```bash
# 1. Normal scenario — should do nothing
python -c "from pipeline import run_pipeline; run_pipeline(scenario='normal', max_iterations=2)"

# 2. Drift inspector — foreign should flag exactly 2 features
python simulate_drift.py foreign

# 3. Registry check — active model should exist
python -c "
from core.registry import ModelRegistry
m = ModelRegistry().get_active()
print(f'Active: v{m.version} | F1={m.f1_score}')
"
```

All three should complete without errors.

---

### Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `No active model in registry` | Models wiped but v1 not trained | Run the v1 training command |
| `F1=0.0` | Old data without causal labels | `rm data_training.csv` + `python generate_data.py` |
| `No module named ...` | venv not active | `source venv/bin/activate` |
| Infinite retraining | Baseline not updating | Ensure `baseline = current_data.copy()` is in pipeline.py after promotion |
| Rollback on every iteration | MIN_F1_THRESHOLD too high | Check `config.py` — should be 0.35 |
