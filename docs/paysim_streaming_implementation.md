# PaySim Self-Healing Pipeline — Complete Implementation Guide

**Goal:** Prove the self-healing algorithm works in a real-world, dynamic scenario by streaming the massive 6.3-million-row Kaggle PaySim dataset chronologically. This completely eliminates "fake" drift scripts and demonstrates the system autonomously detecting organic data shifts over time and healing itself.

**Core Philosophy:** The MLOps algorithmic base (`core/`) remains 100% untouched. All logic is contained in external data streaming and adapter layers.

**Status:** Complete implementation guide with data flow, preprocessing strategy, and roadmap.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Data Flow & Preprocessing](#data-flow--preprocessing)
3. [The 3-Component Architecture](#the-3-component-architecture)
4. [Implementation Phases](#implementation-phases)
5. [Expected Outcome](#expected-outcome)

---

## 1. Architecture Overview

This project is built on the **Open-Closed Principle** using the Adapter Pattern. 

The core ML Engine (`core/drift.py`, `core/healer.py`, `core/retrainer.py`, etc.) is completely blind to the domain it is working on. It does not know if it is looking at credit card fraud, medical records, or telco churn. 

To introduce a new dataset like the Kaggle PaySim dataset (6.3 million rows), **zero changes are required in the core engine**. We simply build a new adapter that acts as a translator between the raw Kaggle CSV and the core engine.

---

## 2. Data Flow & Preprocessing

When the massive PaySim dataset is streamed into the pipeline, it undergoes a two-step cleaning process:

### Step 1: The Adapter (Manual Feature Selection)
The `PaysimAdapter` handles the high-level domain logic. 
*   It explicitly drops the `nameOrig` and `nameDest` columns. These are unique customer IDs. If we passed 6 million unique strings into the ML model, the feature space would explode, crashing the computer's RAM.
*   It defines `"isFraud"` as the target column.
*   It defines `"type"` (CASH_OUT, TRANSFER, etc.) as the categorical column.

### Step 2: The Core Pipeline (Autonomous Math)
Once the adapter hands the data to `core/model.py`, the `scikit-learn` Pipeline takes over:
*   **Numeric Transformer:** Automatically fills missing numbers with the mathematical median and scales them (so a $100,000 transaction doesn't overpower a $5 transaction).
*   **Categorical Transformer:** Automatically fills missing text with `"missing"` and applies One-Hot Encoding to turn text like `"CASH_OUT"` into binary integers.
*   **Data Leakage Prevention:** By doing this inside the ML pipeline, the parameters (like the median) are saved into the `.pkl` file. Live production data is guaranteed to be scored using the exact same mathematical baselines.

---

## 3. The 3-Component Architecture

To simulate a real-world production environment chronologically, we will build three specific components:

### A. The Time Machine (`data/streamer.py`)
Because the dataset is ~500MB, we cannot load it all into RAM.
*   **Sequential Row Chunking:** Uses Pandas to stream data in sequential chunks (e.g., 100,000 rows at a time). This perfectly mimics an infinite stream of unseen production data without the need to calculate complex time windows.
*   **Zero-Fraud Protection:** The streamer ensures that every chunk has enough target cases (fraud) to train the model, automatically appending chunks if necessary.
*   **Memory Management:** Explicitly calls `gc.collect()` after processing each batch to prevent memory leaks during the continuous pipeline loop.

### B. The PaySim Adapter (`adapters/paysim.py`)
Adheres strictly to the `BaseAdapter` contract.
*   `load_baseline()`: Asks the Streamer for Day 1 (Steps 1-24) to train a robust initial `v1.pkl` model.
*   `get_current_data()`: Asks the Streamer for the *next* 24-hour batch, simulating the live daily production stream.

### C. The Simulation Runner (`run_paysim_simulation.py`)
The "Factory Manager" script that runs the entire demonstration.
*   Initializes the adapter and trains the baseline.
*   Runs an infinite loop fetching the next day's data, evaluating drift, and healing the model automatically.
*   **Logging:** Saves every PSI score and Retrain action to a `psi_history.csv` file so a line chart can be visualized later.

---

## 4. Implementation Phases

**Phase 1: Build the Data Streamer (COMPLETE ✅)**
*   Created `data/streamer.py`.
*   Implemented sequential chunked CSV reading using Pandas iterators and garbage collection.
*   Implemented dynamic zero-fraud fallback logic (`min_positive_cases`) to prevent `RandomForest` training crashes.

**Phase 2: Build the Adapter**
*   Create `adapters/paysim.py`.
*   Implement `load_baseline()` and `get_current_data()` using the Streamer.
*   Implement `_preprocess()` to drop the high-cardinality ID columns.

**Phase 3: The Simulation Script**
*   Create `run_paysim_simulation.py`.
*   Wire the loop together.
*   Add clean, color-coded terminal prints to show Day, PSI, and Action taken.

---

## 5. Expected Outcome

When you run the simulation script, you will sit back and watch your terminal:
1.  **Day 1:** Baseline model (`v1.pkl`) trained.
2.  **Days 2-10:** Data streams in. The terminal prints progress: `[Day 2] PSI: 0.05 - Normal`.
3.  **Day X:** An organic shift in the Kaggle dataset occurs. The PSI score spikes to 0.25 (RED alert).
4.  **Autonomous Healing:** The terminal logs the `Healer` kicking in. It retrains on the new batch of data. If the F1 score improves, it deploys `v2.pkl`.
5.  **Metrics Saved:** You will open `psi_history.csv` and see a timeline of your MLOps engine keeping the model alive autonomously.

This proves that you haven't just trained a random forest on a CSV—you have built a fully decoupled, self-sustaining loop capable of ingesting an infinite chronological stream of unseen production data, handling memory constraints gracefully, and healing itself automatically.

---

## 6. Detailed Implementation Guide

Here is the exact step-by-step code breakdown we will use to implement the 3 phases.

### Phase 1: `data/streamer.py` (COMPLETE ✅)
The streamer uses Pandas chunking to read exactly the rows it needs without blowing up memory.
```python
import pandas as pd
import gc

class DataStreamer:
    def __init__(self, csv_path: str, chunk_size: int = 100000):
        self.csv_path = csv_path
        self.chunk_size = chunk_size
        self.iterator = pd.read_csv(csv_path, chunksize=chunk_size)
        self.current_batch_number = 0

    def get_next_batch(self, target_column: str = None, min_positive_cases: int = 10) -> pd.DataFrame:
        accumulated_chunks = []
        positive_count = 0
        
        try:
            while True:
                batch = next(self.iterator)
                accumulated_chunks.append(batch)
                
                if target_column and target_column in batch.columns:
                    positive_count += batch[target_column].sum()
                    if positive_count >= min_positive_cases:
                        break
                else:
                    break
                
            self.current_batch_number += len(accumulated_chunks)
            final_batch = pd.concat(accumulated_chunks, ignore_index=True)
            gc.collect()
            return final_batch
            
        except StopIteration:
            if accumulated_chunks:
                return pd.concat(accumulated_chunks, ignore_index=True)
            raise ValueError("End of streaming data reached.")
```

### Phase 2: `adapters/paysim.py`
The adapter bridges the Kaggle data to your core MLOps engine.
```python
import pandas as pd
from core.adapter import BaseAdapter
from data.streamer import DataStreamer

class PaysimAdapter(BaseAdapter):
    def __init__(self, csv_path: str = "datasets/PS_20174392719_1491204439457_log.csv"):
        self.registry_path = 'models/paysim_registry.db'
        self.streamer = DataStreamer(csv_path)

    @property
    def target_column(self) -> str: return 'isFraud'

    @property
    def categorical_columns(self) -> list[str]: return ['type']

    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop high-cardinality ID columns that break the One-Hot Encoder."""
        cols_to_drop = ['nameOrig', 'nameDest', 'isFlaggedFraud']
        return df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    def load_baseline(self) -> pd.DataFrame:
        raw_df = self.streamer.get_next_batch(batch_hours=24)
        return self._preprocess(raw_df)

    def get_current_data(self) -> pd.DataFrame:
        raw_df = self.streamer.get_next_batch(batch_hours=24)
        return self._preprocess(raw_df)
```

### Phase 3: `run_paysim_simulation.py`
The master script that runs the entire autonomous loop.
```python
import time
import pandas as pd
from adapters.paysim import PaysimAdapter
from core.retrainer import Retrainer
from core.registry import ModelRegistry
from pipeline import SelfHealingPipeline

def main():
    print("🚀 Initializing PaySim Simulation...")
    adapter = PaysimAdapter()
    
    print("⏳ Loading initial 24-hour baseline...")
    baseline_df = adapter.load_baseline()
    
    # Train the initial v1.pkl model
    registry = ModelRegistry(adapter.registry_path)
    retrainer = Retrainer(registry, adapter.categorical_columns)
    retrainer.retrain(baseline_df, adapter.target_column)
    
    print("✅ Baseline v1.pkl trained. Starting autonomous simulation...")
    
    # Initialize the core loop
    pipeline = SelfHealingPipeline(adapter)
    
    # Simulate time passing (Day by Day)
    for day in range(2, 15): # Run for 2 weeks
        print(f"\n--- [ Day {day} ] ---")
        pipeline.run_once()
        # Optionally save PSI metrics to a tracking CSV here
        time.sleep(1) # Small pause for readability

if __name__ == '__main__':
    main()
```
