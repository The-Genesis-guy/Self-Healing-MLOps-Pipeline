# adapters/fraud.py

import numpy as np
import pandas as pd
from core.adapter import BaseAdapter


class FraudAdapter(BaseAdapter):
    """
    Fraud detection domain adapter.
    
    Swap this out for ChurnAdapter, CreditRiskAdapter, etc.
    The core engine never changes — only this file does.
    """

    def __init__(self, scenario: str = 'normal', baseline_path: str = 'data_training.csv'):
        self.scenario = scenario
        self.baseline_path = baseline_path

    @property
    def registry_path(self) -> str:
        return 'models/registry.db'

    @property
    def target_column(self) -> str:
        return 'is_fraud'

    @property
    def categorical_columns(self) -> list[str]:
        return ['merchant_category', 'is_foreign']

    def load_baseline(self) -> pd.DataFrame:
        try:
            return pd.read_csv(self.baseline_path)
        except FileNotFoundError:
            # Generate deterministic in-memory mock data for tests
            n = 1000
            np.random.seed(42)
            df = pd.DataFrame({
                'transaction_amount': np.random.exponential(scale=200, size=n),
                'hour_of_day': np.random.randint(0, 24, size=n),
                'distance_from_home': np.random.exponential(scale=30, size=n),
                'num_transactions_24h': np.random.poisson(lam=3, size=n),
                'is_foreign': np.random.choice([0, 1], size=n, p=[0.9, 0.1]),
                'merchant_category': np.random.choice(['grocery', 'gas', 'online'], size=n),
                'is_fraud': np.random.choice([0, 1], size=n, p=[0.88, 0.12])
            })
            np.random.seed(None) # Reset seed so simulation remains dynamic
            return df

    def get_current_data(self) -> pd.DataFrame:
        baseline = self.load_baseline()
        return self._simulate(baseline, self.scenario)

    def _simulate(self, baseline: pd.DataFrame, scenario: str) -> pd.DataFrame:
        """
        Inject synthetic drift to simulate real-world shifts.
        In production, replace this method with a real data source.
        """
        n = len(baseline)
        current = baseline.copy()

        if scenario == 'normal':
            return baseline.sample(
                n=n, replace=True,
                random_state=np.random.randint(0, 9999)
            ).reset_index(drop=True)

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