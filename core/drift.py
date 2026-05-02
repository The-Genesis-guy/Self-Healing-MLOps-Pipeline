import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict

@dataclass
class DriftReport:
    feature: str
    psi_score: float
    drifted: bool
    baseline_dist: dict
    current_dist: dict

def _psi_numerical(baseline: pd.Series, current: pd.Series, buckets: int = 10) -> tuple:
    """
    PSI for numerical columns.
    
    Step 1: Create bucket edges from baseline data
    Step 2: Count what % of values fall in each bucket (both datasets)
    Step 3: Apply PSI formula per bucket, sum them up
    """
    # Create bucket boundaries using baseline data
    # np.percentile divides baseline into equal-sized buckets
    breakpoints = np.percentile(baseline, np.linspace(0, 100, buckets + 1))
    breakpoints = np.unique(breakpoints)  # remove duplicates (happens with lots of repeated values)

    # Count values per bucket for both datasets
    baseline_counts = np.histogram(baseline, bins=breakpoints)[0]
    current_counts = np.histogram(current, bins=breakpoints)[0]

    # Convert counts to percentages using Laplace Smoothing
    # This avoids division by zero and log(0) without using arbitrary hacks.
    baseline_pct = (baseline_counts + 1) / (len(baseline) + len(baseline_counts))
    current_pct = (current_counts + 1) / (len(current) + len(current_counts))

    # PSI formula: sum of (actual - expected) * ln(actual / expected)
    psi_value = np.sum((baseline_pct - current_pct) * np.log(baseline_pct / current_pct))

    # Build distribution dict for reporting
    bucket_labels = [f"{breakpoints[i]:.1f}-{breakpoints[i+1]:.1f}" for i in range(len(breakpoints)-1)]
    baseline_dist = dict(zip(bucket_labels, baseline_pct.tolist()))
    current_dist = dict(zip(bucket_labels, current_pct.tolist()))

    return psi_value, baseline_dist, current_dist


def _psi_categorical(baseline: pd.Series, current: pd.Series) -> tuple:
    """
    PSI for categorical columns.
    
    No buckets needed — categories are already discrete.
    Just count frequency of each category in both datasets.
    """
    # Get all categories that appear in either dataset
    all_categories = set(baseline.unique()) | set(current.unique())

    baseline_pct = {}
    current_pct = {}

    for cat in all_categories:
        # What % of each dataset is this category? (Laplace Smoothed)
        baseline_pct[cat] = ((baseline == cat).sum() + 1) / (len(baseline) + len(all_categories))
        current_pct[cat] = ((current == cat).sum() + 1) / (len(current) + len(all_categories))

    # Same PSI formula, just over categories instead of buckets
    psi_value = sum(
        (baseline_pct[cat] - current_pct[cat]) * np.log(baseline_pct[cat] / current_pct[cat])
        for cat in all_categories
    )

    return psi_value, baseline_pct, current_pct


def calculate_drift(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    categorical_columns: list,
    threshold: float = 0.1
) -> Dict[str, DriftReport]:
    """
    Run drift detection across all features.
    Returns a report per feature.
    """
    reports = {}

    for column in baseline_df.columns:
        if column not in current_df.columns:
            continue

        if column in categorical_columns:
            psi, baseline_dist, current_dist = _psi_categorical(
                baseline_df[column], current_df[column]
            )
        else:
            psi, baseline_dist, current_dist = _psi_numerical(
                baseline_df[column], current_df[column]
            )

        reports[column] = DriftReport(
            feature=column,
            psi_score=round(psi, 4),
            drifted=psi > threshold,
            baseline_dist=baseline_dist,
            current_dist=current_dist
        )

    return reports