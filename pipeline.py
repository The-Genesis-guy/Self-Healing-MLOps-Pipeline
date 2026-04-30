import time
import logging
import pandas as pd
import numpy as np
from core.drift import calculate_drift
from core.healer import Healer
from core.retrainer import Retrainer
from core.registry import ModelRegistry
from core.model import Model

from config import LOOP_INTERVAL_SECONDS, MAX_RETRAIN_ATTEMPTS
from adapters.fraud import CATEGORICAL_COLUMNS, TARGET_COLUMN, load_baseline, simulate_drift

logger = logging.getLogger(__name__)


def run_pipeline(scenario: str = 'normal', max_iterations: int = 3):
    """
    The main loop.

    scenario      — controls what kind of current data gets simulated
    max_iterations — how many loops to run before stopping (for testing)
                     set to None to run forever in production
    """
    logger.info("=" * 60)
    logger.info("  Self-Healing MLOps Pipeline — Starting")
    logger.info("=" * 60)

    # --- Setup ---
    registry = ModelRegistry()
    healer = Healer()
    retrainer = Retrainer(registry=registry, categorical_columns=CATEGORICAL_COLUMNS)
    baseline = load_baseline()

    iteration = 0
    consecutive_failed_retrains = 0   # tracks how many retrains in a row were rejected

    while True:
        iteration += 1
        logger.info(f"\n--- Iteration {iteration} ---")

        # --- Step 1: OBSERVE ---
        active = registry.get_active()
        if active is None:
            logger.error("[ERROR] No active model in registry. Run training first.")
            break
        logger.info(f"[OBSERVE] Active model: v{active.version} | F1={active.f1_score}")

        current_data = simulate_drift(baseline, scenario)

        # --- Step 2: COMPARE ---
        # Target column excluded — in production you never have labels on incoming live data.
        drift_reports = calculate_drift(
            baseline.drop(columns=[TARGET_COLUMN]),
            current_data.drop(columns=[TARGET_COLUMN]),
            categorical_columns=CATEGORICAL_COLUMNS
        )

        drifted = [f for f, r in drift_reports.items() if r.drifted]
        logger.info(f"[COMPARE] Drifted features: {drifted if drifted else 'none'}")

        # --- Step 3: DECIDE ---
        decision = healer.decide(drift_reports, current_f1=active.f1_score)
        level = logging.WARNING if decision.action != 'none' else logging.INFO
        logger.log(level, f"[DECIDE]  Action={decision.action} | {decision.reason}")

        # --- Step 4: ACT ---
        if decision.action == 'retrain':
            if consecutive_failed_retrains >= MAX_RETRAIN_ATTEMPTS:
                logger.warning(f"[ACT]     ⏸️  Retrain suppressed — {MAX_RETRAIN_ATTEMPTS} consecutive failures.")
                logger.warning(f"[ACT]     📊 Drift acknowledged. Monitoring without retraining.")
            else:
                logger.info("[ACT]     Retraining on current data...")
                result = retrainer.retrain(current_data, target_column=TARGET_COLUMN)
                if result.promoted:
                    consecutive_failed_retrains = 0
                    logger.info(f"[ACT]     ✅ New model v{result.new_version} promoted. F1: {result.old_f1} → {result.new_f1}")
                    baseline = current_data.copy()
                    logger.info(f"[ACT]     📐 Baseline updated to reflect new data distribution.")
                else:
                    consecutive_failed_retrains += 1
                    logger.warning(f"[ACT]     ❌ New model rejected. F1: {result.new_f1} did not beat {result.old_f1}")
                    logger.warning(f"[ACT]     🔁 Failed attempt {consecutive_failed_retrains}/{MAX_RETRAIN_ATTEMPTS}")

        elif decision.action == 'rollback':
            all_models = registry.get_all()
            if len(all_models) >= 2:
                previous = all_models[-2]
                registry.set_active(previous.version)
                logger.warning(f"[ACT]     ⏪ Rolled back to v{previous.version} | F1={previous.f1_score}")
            else:
                logger.warning("[ACT]     ⚠️  No previous version to roll back to.")

        elif decision.action == 'alert':
            logger.warning(f"[ACT]     ⚠️  Alert: {decision.reason}")

        else:
            consecutive_failed_retrains = 0
            logger.info("[ACT]     ✅ No action needed.")

        # --- Step 5: VERIFY ---
        active_after = registry.get_active()
        logger.info(f"[VERIFY]  Active model after action: v{active_after.version} | F1={active_after.f1_score}")

        if max_iterations and iteration >= max_iterations:
            logger.info(f"\nReached {max_iterations} iterations. Stopping.")
            break

        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    # Configure logging when running as a standalone script
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s"   # plain output — matches old print() style for CLI use
    )
    run_pipeline(scenario='normal', max_iterations=3)