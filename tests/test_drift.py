#tests PSI calculations

import numpy as np
import pandas as pd
from core.drift import calculate_drift

def make_df(n=500, seed=0, **overrides):
    rng = np.random.RandomState(seed)
    df = pd.DataFrame({
        "amount": rng.exponential(200, n),
        "hour":   rng.randint(0, 24, n),
        "cat":    rng.choice(["a", "b", "c"], n),
    })
    for col, val in overrides.items():
        df[col] = val
    return df

def test_identical_data_has_near_zero_psi():
    df = make_df(seed=42)
    reports = calculate_drift(df, df, categorical_columns=["cat"])
    for feature, report in reports.items():
        assert report.psi_score < 0.05, f"{feature} PSI={report.psi_score} — expected near 0"

def test_identical_data_not_flagged_as_drifted():
    df = make_df(seed=42)
    reports = calculate_drift(df, df, categorical_columns=["cat"])
    for feature, report in reports.items():
        assert not report.drifted

def test_shifted_distribution_detected():
    baseline = make_df(seed=1)
    # Massively shift amount — should flag as drifted
    current = make_df(seed=2, amount=np.random.exponential(5000, 500))
    reports = calculate_drift(baseline, current, categorical_columns=["cat"])
    assert reports["amount"].drifted

def test_unshifted_features_not_flagged():
    baseline = make_df(seed=1)
    current  = make_df(seed=2, amount=np.random.exponential(5000, 500))
    reports = calculate_drift(baseline, current, categorical_columns=["cat"])
    # hour and cat should be fine
    assert not reports["hour"].drifted
    assert not reports["cat"].drifted
