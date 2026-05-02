import pytest
import os
from adapters.paysim import PaysimAdapter

# We only run this test if the Kaggle PaySim dataset is present in the root directory
@pytest.mark.skipif(not os.path.exists("PS_20174392719_1491204439457_log.csv"), 
                    reason="Kaggle PaySim dataset not found")
def test_paysim_adapter_can_load_chunks():
    """
    Verify that the real Kaggle dataset can be streamed safely.
    Tests baseline loading, chunking, and memory-safe preprocessing.
    """
    adapter = PaysimAdapter()
    
    # 1. Test baseline load (first 100k chunk)
    baseline = adapter.load_baseline()
    assert not baseline.empty
    assert len(baseline) >= 100000
    assert 'isFraud' in baseline.columns
    
    # 2. Verify IDs were dropped correctly (Critical for OOM prevention)
    assert 'nameOrig' not in baseline.columns
    assert 'nameDest' not in baseline.columns
    assert 'isFlaggedFraud' not in baseline.columns
    
    # 3. Test subsequent chunk load
    current = adapter.get_current_data()
    assert not current.empty
    assert len(current) >= 100000
    assert 'isFraud' in current.columns
