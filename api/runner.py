# pipeline loop in a background thread

import threading
import time
import pandas as pd
from core.drift import calculate_drift
from core.healer import Healer
from core.retrainer import Retrainer
from core.registry import ModelRegistry
from core.model import Model
from core.history import HistoryLogger
from core.validator import DataValidator
from config import LOOP_INTERVAL_SECONDS, MAX_RETRAIN_ATTEMPTS
from api.state import pipeline_state

_stop_event = threading.Event()
_thread: threading.Thread = None


def _loop(adapter):
    registry = ModelRegistry(db_path=adapter.registry_path)
    healer = Healer()
    retrainer = Retrainer(
        registry=registry,
        categorical_columns=adapter.categorical_columns
    )
    history = HistoryLogger()
    validator = DataValidator()
    baseline = adapter.load_baseline()
    
    shadow_version = None  # Track the candidate version awaiting trial
    shadow_model = None    # The model object for evaluation
    pipeline_state.update(running=True, iteration=0)

    consecutive_failed_retrains = 0

    try:
        while not _stop_event.is_set():
            iteration = pipeline_state.iteration + 1
            pipeline_state.update(iteration=iteration)

            # OBSERVE
            active = registry.get_active()
            if active is None:
                break
            pipeline_state.update(
                active_model_version=active.version,
                active_model_f1=active.f1_score
            )

            current_data = adapter.get_current_data()
            
            # --- VALIDATE (The Guardrail) ---
            valid = validator.validate(current_data, target_column=adapter.target_column)
            if not valid.is_valid:
                pipeline_state.update(health="critical", last_reason=f"DATA QUALITY ALERT: {valid.issues[0]}")
                history.log(iteration, active.version, active.f1_score, 0.0, "alert", valid.reason)
                break

            # --- SHADOW TRIAL (The Safety Trial) ---
            if shadow_version and shadow_model:
                y_true = current_data[adapter.target_column]
                X = current_data.drop(columns=[adapter.target_column])
                
                from sklearn.metrics import f1_score
                
                # Active vs Shadow
                active_model_obj = Model.load(active.path)
                active_preds = active_model_obj.predict(X)
                active_f1_new = f1_score(y_true, active_preds, zero_division=0)
                
                shadow_preds = shadow_model.predict(X)
                shadow_f1_new = f1_score(y_true, shadow_preds, zero_division=0)
                
                if shadow_f1_new > active_f1_new:
                    registry.set_active(shadow_version)
                    history.log(iteration, shadow_version, shadow_f1_new, 0.0, "promote", 
                                f"Shadow v{shadow_version} beat Active v{active.version} in trial.")
                else:
                    history.log(iteration, active.version, active_f1_new, 0.0, "discard", 
                                f"Shadow v{shadow_version} failed trial.")
                
                shadow_version = None
                shadow_model = None
                pipeline_state.update(shadow_model_version=None)
                active = registry.get_active()

            # COMPARE
            drift_reports = calculate_drift(
                baseline.drop(columns=[adapter.target_column]),
                current_data.drop(columns=[adapter.target_column]),
                categorical_columns=adapter.categorical_columns
            )
            drifted = [f for f, r in drift_reports.items() if r.drifted]
            max_drift = max([r.psi_score for r in drift_reports.values()]) if drift_reports else 0

            # DECIDE
            decision = healer.decide(drift_reports, current_f1=active.f1_score)
            pipeline_state.update(
                last_action=decision.action,
                last_reason=decision.reason,
                last_drifted_features=drifted
            )

            # ACT
            if decision.action == 'retrain':
                if consecutive_failed_retrains >= MAX_RETRAIN_ATTEMPTS:
                    pipeline_state.update(health="critical", last_reason="SAFE MODE: Retraining failed 3 times.")
                    history.log(iteration, active.version, active.f1_score, max_drift, "safe_mode", "Retraining failed 3 times. Entering Safe Mode.")
                    break
                else:
                    retrain_res = retrainer.retrain(current_data, target_column=adapter.target_column)
                    if retrain_res.promoted:
                        shadow_version = retrain_res.new_version
                        record = registry.get_by_version(shadow_version)
                        shadow_model = Model.load(record.path)
                        pipeline_state.update(
                            last_action="shadow",
                            shadow_model_version=shadow_version,
                            last_reason=f"v{shadow_version} in Shadow Trial."
                        )
                        history.log(iteration, active.version, active.f1_score, max_drift, "shadow", f"v{shadow_version} training done.")
                        consecutive_failed_retrains = 0
                    else:
                        consecutive_failed_retrains += 1
                        history.log(iteration, active.version, active.f1_score, max_drift, "failed_retrain", retrain_res.reason)

            elif decision.action == 'rollback':
                all_models = registry.get_all()
                if len(all_models) >= 2:
                    previous = all_models[-2]
                    registry.set_active(previous.version)
                    history.log(iteration, previous.version, previous.f1_score, max_drift, "rollback", decision.reason)
            else:
                consecutive_failed_retrains = 0
                history.log(iteration, active.version, active.f1_score, max_drift, decision.action, decision.reason)

            _stop_event.wait(timeout=LOOP_INTERVAL_SECONDS)
            
    except Exception as e:
        pipeline_state.update(last_reason=f"CRASH: {str(e)}")
    finally:
        pipeline_state.update(running=False)


def start(adapter):
    global _thread
    if pipeline_state.running: return False
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, args=(adapter,), daemon=True)
    _thread.start()
    return True

def stop():
    _stop_event.set()
    return True
