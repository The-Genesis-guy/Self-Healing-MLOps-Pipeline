import pytest
import pandas as pd
import numpy as np
from core.validator import DataValidator

@pytest.fixture
def validator():
    return DataValidator(null_threshold=0.1)

def test_valid_data_passes(validator):
    df = pd.DataFrame({
        'amount': [100.0, 200.0, 300.0],
        'hour_of_day': [10, 11, 12],
        'type': ['TRANSFER', 'CASH_OUT', 'PAYMENT']
    })
    result = validator.validate(df)
    assert result.is_valid is True

def test_empty_df_fails(validator):
    df = pd.DataFrame()
    result = validator.validate(df)
    assert result.is_valid is False
    assert "empty" in result.reason

def test_null_threshold_fails(validator):
    df = pd.DataFrame({
        'amount': [100.0, None, None], # 66% null
        'hour_of_day': [10, 11, 12]
    })
    result = validator.validate(df)
    assert result.is_valid is False
    assert "nulls" in result.issues[0]

def test_constant_column_fails(validator):
    df = pd.DataFrame({
        'amount': [100.0, 100.0, 100.0], # constant
        'hour_of_day': [10, 11, 12]
    })
    result = validator.validate(df)
    assert result.is_valid is False
    assert "constant" in result.issues[0]

def test_out_of_bounds_fails(validator):
    df = pd.DataFrame({
        'amount': [-10.0, 200.0, 300.0], # negative amount
        'hour_of_day': [10, 11, 12]
    })
    result = validator.validate(df)
    assert result.is_valid is False
    assert "negative" in result.issues[0]
