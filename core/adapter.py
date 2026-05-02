#This is the contract. Every adapter must follow this shape.
 
from abc import ABC, abstractmethod
import pandas as pd


class BaseAdapter(ABC):
    """
    The contract every domain adapter must follow.
    
    To apply this pipeline to a new domain:
    1. Create a new file in adapters/
    2. Inherit from BaseAdapter
    3. Implement these 4 methods
    4. Pass it to run_pipeline()
    
    The core engine never changes.
    """

    @property
    @abstractmethod
    def target_column(self) -> str:
        """
        The column the model is trying to predict.
        Example: 'is_fraud', 'churned', 'will_default'
        """
        ...

    @property
    @abstractmethod
    def categorical_columns(self) -> list[str]:
        """
        Columns that are categories, not numbers.
        PSI is calculated differently for these.
        Example: ['merchant_category', 'is_foreign']
        """
        ...

    @abstractmethod
    def load_baseline(self) -> pd.DataFrame:
        """
        Load the reference dataset — the data the model was trained on.
        This is what 'normal' looks like.
        """
        ...

    @abstractmethod
    def get_current_data(self) -> pd.DataFrame:
        """
        Return the current incoming data.
        In production: read from a database or stream.
        In testing: simulate drift scenarios.
        """
        ...

    @property
    def registry_path(self) -> str:
        """Path to this domain's SQLite registry. Override to use a separate DB."""
        return 'models/registry.db'