# pipeline loop in a background thread

import threading
import time
import pandas as pd
from core.drift import calculate_drift
from core.healer import Healer
from core.retrainer import Retrainer
from core.registry import ModelRegistry
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
    baseline = adapter.load_baseline()
    pipeline_state.update(running=True, iteration=0)

    consecutive_failed_retrains = 0

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

        # COMPARE — drop target column, we never have labels on live data
        current_data = adapter.get_current_data()
        drift_reports = calculate_drift(
            baseline.drop(columns=[adapter.target_column]),
            current_data.drop(columns=[adapter.target_column]),
            categorical_columns=adapter.categorical_columns
        )
        drifted = [f for f, r in drift_reports.items() if r.drifted]

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
                pass   # suppress — drift acknowledged, monitoring only
            else:
                result = retrainer.retrain(current_data, target_column=adapter.target_column)
                if result.promoted:
                    consecutive_failed_retrains = 0
                    baseline = current_data.copy()
                    pipeline_state.update(
                        active_model_version=result.new_version,
                        active_model_f1=result.new_f1
                    )
                else:
                    consecutive_failed_retrains += 1

        elif decision.action == 'rollback':
            all_models = registry.get_all()
            if len(all_models) >= 2:
                previous = all_models[-2]
                registry.set_active(previous.version)
                pipeline_state.update(
                    active_model_version=previous.version,
                    active_model_f1=previous.f1_score
                )

        else:
            consecutive_failed_retrains = 0   # drift cleared — reset counter

        _stop_event.wait(timeout=LOOP_INTERVAL_SECONDS)

    pipeline_state.update(running=False)


def start(adapter):
    global _thread
    if pipeline_state.running:
        return False   # already running
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, args=(adapter,), daemon=True)
    _thread.start()
    return True


def stop():
    _stop_event.set()
    return True
