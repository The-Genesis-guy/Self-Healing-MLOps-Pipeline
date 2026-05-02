import pandas as pd
from core.adapter import BaseAdapter
from data.streamer import DataStreamer

class PaysimAdapter(BaseAdapter):
    """
    Adapter for the Kaggle PaySim Mobile Money Fraud dataset.
    Converts the 6.3 Million row CSV into chronological streaming chunks
    for the self-healing ML engine.
    """
    def __init__(self, csv_path: str = "PS_20174392719_1491204439457_log.csv"):
        # Create a dedicated SQLite registry just for the PaySim simulation
        self._registry_path = 'models/paysim_registry.db'
        
        # Initialize the chronological streamer
        self.streamer = DataStreamer(csv_path=csv_path, chunk_size=100000)

    @property
    def registry_path(self) -> str:
        return self._registry_path

    @property
    def target_column(self) -> str:
        return 'isFraud'

    @property
    def categorical_columns(self) -> list[str]:
        return ['type']

    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        CRITICAL: Drop high-cardinality ID columns.
        If we attempt to One-Hot Encode millions of unique 'nameOrig' strings,
        the Pipeline will cause a catastrophic Out-Of-Memory (OOM) error.
        We also drop 'isFlaggedFraud' as it is effectively a label.
        """
        cols_to_drop = ['nameOrig', 'nameDest', 'isFlaggedFraud']
        # Only drop columns if they actually exist in the dataframe
        return df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    def load_baseline(self) -> pd.DataFrame:
        """
        Loads the very first chronological chunk of data to serve as 
        the mathematical baseline for the 'v1.pkl' model.
        """
        # Ensure we have enough positive cases to train a valid initial model
        raw_df = self.streamer.get_next_batch(target_column=self.target_column, min_positive_cases=10)
        return self._preprocess(raw_df)

    def get_current_data(self) -> pd.DataFrame:
        """
        Fetches the next chronological chunk of data.
        Simulates an incoming live production data stream.
        """
        raw_df = self.streamer.get_next_batch(target_column=self.target_column, min_positive_cases=10)
        return self._preprocess(raw_df)
