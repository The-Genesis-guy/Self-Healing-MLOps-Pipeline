import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    is_valid: bool
    reason: str = ""
    issues: list[str] = None

class DataValidator:
    """
    The 'Bouncer' of the pipeline. 
    Prevents the system from retraining on corrupted or 'garbage' data.
    """
    def __init__(self, null_threshold: float = 0.1):
        self.null_threshold = null_threshold

    def validate(self, df: pd.DataFrame, target_column: str = None) -> ValidationResult:
        issues = []
        
        # 1. Check for Empty Data
        if df.empty:
            return ValidationResult(False, "Dataframe is empty.")

        # 2. Check for High Null Counts
        null_pct = df.isnull().mean()
        for col, pct in null_pct.items():
            if pct > self.null_threshold:
                issues.append(f"Column '{col}' has {pct:.1%} nulls (Threshold: {self.null_threshold:.1%})")

        # 3. Check for Constant Columns (Broken Data Pipe)
        # We exclude the target column from this check as it might be constant in small batches
        feature_cols = [c for c in df.columns if c != target_column]
        for col in feature_cols:
            if df[col].nunique() <= 1:
                issues.append(f"Column '{col}' is constant (potential broken data pipe)")

        # 4. Domain Specific Bounds (Basic)
        if 'amount' in df.columns:
            if (df['amount'] < 0).any():
                issues.append("Found negative values in 'amount'")
        
        if 'hour_of_day' in df.columns:
            if (df['hour_of_day'] > 23).any() or (df['hour_of_day'] < 0).any():
                issues.append("Found out-of-bounds values in 'hour_of_day'")

        if not issues:
            return ValidationResult(True, "Data passed quality checks.")
        
        return ValidationResult(False, "Data quality checks failed.", issues)
