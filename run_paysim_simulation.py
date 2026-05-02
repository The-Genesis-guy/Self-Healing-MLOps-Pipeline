import time
import logging
from adapters.paysim import PaysimAdapter
from core.registry import ModelRegistry
from core.retrainer import Retrainer
from pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def setup_baseline(adapter):
    """
    Ensures that a baseline 'v1.pkl' model exists before starting the pipeline.
    It grabs the first 100,000 rows from the streamer to train the Random Forest.
    """
    logger.info("⏳ Loading initial 100k rows to train the v1.pkl baseline...")
    baseline_df = adapter.load_baseline()
    
    registry = ModelRegistry(db_path=adapter.registry_path)
    retrainer = Retrainer(registry=registry, categorical_columns=adapter.categorical_columns)
    
    # If there is no active model in the database, we must train one
    if registry.get_active() is None:
        logger.info("🧠 Training initial Random Forest model (this may take a few seconds)...")
        result = retrainer.retrain(baseline_df, target_column=adapter.target_column)
        logger.info(f"✅ Baseline v{result.new_version} trained successfully. Initial F1 Score: {result.new_f1:.4f}")
    else:
        active = registry.get_active()
        logger.info(f"✅ Baseline already exists: v{active.version} (F1: {active.f1_score:.4f})")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 KAGGLE PAYSIM SELF-HEALING SIMULATION")
    logger.info("=" * 60)
    
    adapter = PaysimAdapter()
    
    # 1. Train the initial model using the very first 100,000 rows
    setup_baseline(adapter)
    
    # 2. Run the infinite self-healing loop for the remaining 6.2 Million rows
    # We set max_iterations to 62 because (62 * 100k) + the baseline 100k = 6.3 Million rows.
    logger.info("\n🚀 Launching Autonomous Pipeline...")
    time.sleep(2)  # Pause for dramatic effect so you can read the terminal
    
    try:
        run_pipeline(adapter=adapter, max_iterations=62)
    except ValueError as e:
        # The streamer will raise a ValueError when it hits the end of the 6.3M row file
        logger.info(f"\n🎉 SIMULATION COMPLETE: {e}")
