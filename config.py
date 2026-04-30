# All tunable parameters in one place.
# Change values here — nothing else needs to be touched.

# --- Drift Detection ---
DRIFT_ALERT_THRESHOLD   = 0.10   # PSI above this → mild drift, alert
DRIFT_RETRAIN_THRESHOLD = 0.20   # PSI above this → severe drift, retrain

# --- Model Performance ---
MIN_F1_THRESHOLD = 0.35          # F1 below this → rollback immediately

# --- Pipeline ---
LOOP_INTERVAL_SECONDS = 5        # seconds to wait between iterations
MAX_RETRAIN_ATTEMPTS  = 3        # stop retrying after this many consecutive failed retrains