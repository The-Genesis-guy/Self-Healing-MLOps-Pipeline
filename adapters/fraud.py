# Everything domain-specific lives here.
# To switch domains, add a new adapter file — the core engine stays untouched.

import numpy as np
import pandas as pd

CATEGORICAL_COLUMNS = ['merchant_category', 'is_foreign']
TARGET_COLUMN = 'is_fraud'
BASELINE_PATH = 'data_training.csv'


def load_baseline() -> pd.DataFrame:
    return pd.read_csv(BASELINE_PATH)


def simulate_drift(baseline: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """
    Inject synthetic drift to simulate real-world shifts.

    Scenarios:
    - 'normal'      → data matches baseline, no drift
    - 'night_shift' → fraud moves to 2am–5am
    - 'high_value'  → transaction amounts jump to $3000+ range
    - 'foreign'     → spike in foreign card transactions
    """
    n = len(baseline)
    current = baseline.copy()

    if scenario == 'normal':
        return baseline.sample(n=n, replace=True,
                               random_state=np.random.randint(0, 9999)).reset_index(drop=True)

    elif scenario == 'night_shift':
        current['hour_of_day'] = np.random.choice(range(2, 6), size=n)
        return current

    elif scenario == 'high_value':
        current['transaction_amount'] = np.random.exponential(scale=3000, size=n)
        return current

    elif scenario == 'foreign':
        current['is_foreign'] = np.random.choice([0, 1], size=n, p=[0.2, 0.8])
        current['transaction_amount'] = np.random.exponential(scale=5000, size=n)
        return current

    return baseline.copy()