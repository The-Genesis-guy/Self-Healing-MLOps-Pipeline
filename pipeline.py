# pipeline.py

import time
import logging
import pandas as pd
from core.adapter import BaseAdapter
from core.drift import calculate_drift
from core.healer import Healer
from core.retrainer import Retrainer
from core.registry import ModelRegistry
from config import LOOP_INTERVAL_SECONDS, MAX_RETRAIN_ATTEMPTS

logger = logging.getLogger(__name__)


def run_pipeline(adapter: BaseAdapter, max_iterations: int = 3):
    """
    The main loop. Completely domain-agnostic.
    Pass any adapter and it works.

    Examples:
        run_pipeline(adapter=FraudAdapter(scenario='foreign'))
        run_pipeline(adapter=ChurnAdapter())
        run_pipeline(adapter=CreditRiskAdapter(scenario='recession'))
    """
    logger.info("=" * 60)
    logger.info("  Self-Healing MLOps Pipeline — Starting")
    logger.info(f"  Adapter : {adapter.__class__.__name__}")
    logger.info("=" * 60)

    registry = ModelRegistry(db_path=adapter.registry_path)
    healer = Healer()
    retrainer = Retrainer(
        registry=registry,
        categorical_columns=adapter.categorical_columns
    )
    baseline = adapter.load_baseline()

    iteration = 0
    consecutive_failed_retrains = 0

    while True:
        iteration += 1
        logger.info(f"\n--- Iteration {iteration} ---")

        # --- OBSERVE ---
        active = registry.get_active()
        if active is None:
            logger.error("[ERROR] No active model. Run training first.")
            break
        logger.info(f"[OBSERVE] Active model: v{active.version} | F1={active.f1_score}")

        current_data = adapter.get_current_data()

        # --- COMPARE ---
        # Drop target — never available on live incoming data
        drift_reports = calculate_drift(
            baseline.drop(columns=[adapter.target_column]),
            current_data.drop(columns=[adapter.target_column]),
            categorical_columns=adapter.categorical_columns
        )

        drifted = [f for f, r in drift_reports.items() if r.drifted]
        logger.info(f"[COMPARE] Drifted features: {drifted if drifted else 'none'}")

        # --- DECIDE ---
        decision = healer.decide(drift_reports, current_f1=active.f1_score)
        level = logging.WARNING if decision.action != 'none' else logging.INFO
        logger.log(level, f"[DECIDE]  Action={decision.action} | {decision.reason}")

        # --- ACT ---
        if decision.action == 'retrain':
            if consecutive_failed_retrains >= MAX_RETRAIN_ATTEMPTS:
                logger.warning(f"[ACT]     ⏸️  Retrain suppressed — {MAX_RETRAIN_ATTEMPTS} consecutive failures.")
                logger.warning(f"[ACT]     🚨 HUMAN INTERVENTION REQUIRED — drift cannot be resolved automatically.")

            else:
                logger.info("[ACT]     Retraining on current data...")
                result = retrainer.retrain(current_data, target_column=adapter.target_column)
                if result.promoted:
                    consecutive_failed_retrains = 0
                    logger.info(f"[ACT]     ✅ New model v{result.new_version} promoted. F1: {result.old_f1} → {result.new_f1}")
                    baseline = current_data.copy()
                    logger.info(f"[ACT]     📐 Baseline updated.")
                else:
                    consecutive_failed_retrains += 1
                    logger.warning(f"[ACT]     ❌ Rejected. F1: {result.new_f1} did not beat {result.old_f1}")
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

        # --- VERIFY ---
        active_after = registry.get_active()
        logger.info(f"[VERIFY]  Active model after action: v{active_after.version} | F1={active_after.f1_score}")

        if max_iterations and iteration >= max_iterations:
            logger.info(f"\nReached {max_iterations} iterations. Stopping.")
            break

        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Change this one line to switch domains
    from adapters.fraud import FraudAdapter
    run_pipeline(adapter=FraudAdapter(scenario='normal'), max_iterations=3)