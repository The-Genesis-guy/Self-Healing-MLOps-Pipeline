import logging
import time
import pandas as pd
from sklearn.metrics import f1_score
from core.drift import calculate_drift
from core.healer import Healer
from core.retrainer import Retrainer
from core.registry import ModelRegistry
from core.model import Model
from core.history import HistoryLogger
from core.validator import DataValidator
from config import LOOP_INTERVAL_SECONDS, MAX_RETRAIN_ATTEMPTS

logger = logging.getLogger(__name__)

def run_pipeline(adapter, max_iterations=None):
    """
    The unified Self-Healing Loop.
    Supports Shadow Deployment, Safe Mode, and Persistence.
    """
    registry = ModelRegistry(db_path=adapter.registry_path)
    healer = Healer()
    retrainer = Retrainer(
        registry=registry,
        categorical_columns=adapter.categorical_columns
    )
    history = HistoryLogger()
    validator = DataValidator()
    baseline = adapter.load_baseline()

    iteration = 0
    consecutive_failed_retrains = 0
    
    shadow_version = None
    shadow_model = None

    while True:
        iteration += 1
        if max_iterations and iteration > max_iterations:
            break
            
        logger.info(f"\n--- Iteration {iteration} ---")

        # --- OBSERVE ---
        active = registry.get_active()
        if active is None:
            logger.error("[ERROR] No active model.")
            break
        logger.info(f"[OBSERVE] Active model: v{active.version} | F1={active.f1_score}")

        current_data = adapter.get_current_data()
        
        # --- VALIDATE ---
        valid = validator.validate(current_data, target_column=adapter.target_column)
        if not valid.is_valid:
            logger.error(f"[ERROR]   🚨 DATA QUALITY ALERT: {valid.reason}")
            history.log(iteration, active.version, active.f1_score, 0.0, "alert", valid.reason)
            break

        # --- SHADOW TRIAL ---
        if shadow_version and shadow_model:
            y_true = current_data[adapter.target_column]
            X = current_data.drop(columns=[adapter.target_column])
            
            active_model_obj = Model.load(active.path)
            active_preds = active_model_obj.predict(X)
            active_f1_new = f1_score(y_true, active_preds, zero_division=0)
            
            shadow_preds = shadow_model.predict(X)
            shadow_f1_new = f1_score(y_true, shadow_preds, zero_division=0)
            
            if shadow_f1_new > active_f1_new:
                logger.info(f"[ACT]     ✅ Shadow v{shadow_version} beat Active v{active.version}. Promoting!")
                registry.set_active(shadow_version)
                history.log(iteration, shadow_version, shadow_f1_new, 0.0, "promote", "Shadow trial win.")
            else:
                logger.info(f"[ACT]     ❌ Shadow v{shadow_version} failed trial. Discarding.")
                history.log(iteration, active.version, active_f1_new, 0.0, "discard", "Shadow trial loss.")
            
            shadow_version = None
            shadow_model = None
            active = registry.get_active()

        # --- COMPARE ---
        drift_reports = calculate_drift(
            baseline.drop(columns=[adapter.target_column]),
            current_data.drop(columns=[adapter.target_column]),
            categorical_columns=adapter.categorical_columns
        )
        max_drift = max([r.psi_score for r in drift_reports.values()]) if drift_reports else 0

        # --- DECIDE ---
        decision = healer.decide(drift_reports, current_f1=active.f1_score)
        
        # --- ACT ---
        if decision.action == 'retrain':
            if consecutive_failed_retrains >= MAX_RETRAIN_ATTEMPTS:
                logger.error("[ERROR]   🚨 SAFE MODE: Retraining failed 3 times.")
                history.log(iteration, active.version, active.f1_score, max_drift, "safe_mode", "Retraining failed 3 times. Entering Safe Mode.")
                break
            else:
                retrain_res = retrainer.retrain(current_data, target_column=adapter.target_column)
                if retrain_res.promoted:
                    shadow_version = retrain_res.new_version
                    record = registry.get_by_version(shadow_version)
                    shadow_model = Model.load(record.path)
                    logger.info(f"[ACT]     🟡 Model v{shadow_version} in Shadow Trial.")
                    history.log(iteration, active.version, active.f1_score, max_drift, "shadow", f"v{shadow_version} candidate.")
                    consecutive_failed_retrains = 0
                else:
                    consecutive_failed_retrains += 1
                    logger.warning(f"[ACT]     🔁 Failed attempt {consecutive_failed_retrains}/3")
                    history.log(iteration, active.version, active.f1_score, max_drift, "failed_retrain", retrain_res.reason)

        elif decision.action == 'rollback':
            all_models = registry.get_all()
            if len(all_models) >= 2:
                previous = all_models[-2]
                registry.set_active(previous.version)
                logger.info(f"[ACT]     ⏪ Rolled back to v{previous.version}")
                history.log(iteration, previous.version, previous.f1_score, max_drift, "rollback", decision.reason)

        else:
            consecutive_failed_retrains = 0
            history.log(iteration, active.version, active.f1_score, max_drift, decision.action, decision.reason)

        time.sleep(LOOP_INTERVAL_SECONDS)