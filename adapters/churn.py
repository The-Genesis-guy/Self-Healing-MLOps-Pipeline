# adapters/churn.py

import numpy as np
import pandas as pd
from core.adapter import BaseAdapter


class ChurnAdapter(BaseAdapter):

    def __init__(self, scenario: str = 'normal', baseline_path: str = 'data_churn.csv'):
        self.scenario = scenario
        self.baseline_path = baseline_path

    @property
    def registry_path(self) -> str:
        return 'models/churn_registry.db'

    @property
    def target_column(self) -> str:
        return 'churned'

    @property
    def categorical_columns(self) -> list[str]:
        return ['contract_type']   # matches what generate_churn_data.py actually creates

    def load_baseline(self) -> pd.DataFrame:
        return pd.read_csv(self.baseline_path)

    def get_current_data(self) -> pd.DataFrame:
        baseline = self.load_baseline()
        return self._simulate(baseline, self.scenario)

    def _simulate(self, baseline: pd.DataFrame, scenario: str) -> pd.DataFrame:
        """
        Drift scenarios for churn:
        - normal       → same distribution, no drift
        - price_hike   → monthly_charges jumps (company raises prices)
        - support_drop → num_support_calls spikes (product quality drops)
        - contract_shift → customers move to monthly contracts (less loyalty)
        """
        n = len(baseline)
        current = baseline.copy()

        if scenario == 'normal':
            return baseline.sample(
                n=n, replace=True,
                random_state=np.random.randint(0, 9999)
            ).reset_index(drop=True)

        elif scenario == 'price_hike':
            # Prices jump — monthly_charges shifts up significantly
            current['monthly_charges'] = np.random.normal(110, 20, size=n).clip(80, 150)
            return current

        elif scenario == 'support_drop':
            # Product quality drops — support calls spike
            current['num_support_calls'] = np.random.poisson(lam=7, size=n)
            return current

        elif scenario == 'contract_shift':
            # Customers move away from long contracts
            current['contract_type'] = np.random.choice(
                ['monthly', 'yearly', 'two_year'],
                size=n,
                p=[0.85, 0.10, 0.05]   # was [0.5, 0.3, 0.2]
            )
            return current

        return baseline.copy()