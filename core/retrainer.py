import pandas as pd
from dataclasses import dataclass
from core.model import Model
from core.registry import ModelRegistry


@dataclass
class RetrainResult:
    """The outcome of a retrain attempt."""
    promoted: bool          # True if new model replaced the old one
    old_version: int        # version number of the model before retraining
    new_version: int        # version number of the newly trained model
    old_f1: float           # F1 of the old model
    new_f1: float           # F1 of the new model
    reason: str             # why it was promoted or rejected


class Retrainer:
    def __init__(self, registry: ModelRegistry, categorical_columns: list[str],
                 models_dir: str = "models"):
        self.registry = registry
        self.models_dir = models_dir
        # categorical_columns tells us which columns need encoding before training
        # This is domain knowledge passed in from outside — retrainer itself stays generic
        self.categorical_columns = categorical_columns

    def retrain(self, new_data: pd.DataFrame, target_column: str) -> RetrainResult:
        """
        Trains a new model on new_data and decides whether to promote it.

        Promotion rule: new model must have HIGHER F1 than the current active model.
        Accuracy is ignored here — we already learned why F1 matters more for imbalanced data.

        If no active model exists yet (first ever training), promote unconditionally.
        """

        # --- Step 1: Get the current active model's performance ---
        # We need this to compare against after training
        active = self.registry.get_active()

        if active is None:
            # No model exists yet — anything we train gets promoted automatically
            old_f1 = 0.0
            old_version = 0
        else:
            old_f1 = active.f1_score
            old_version = active.version

        # --- Step 2: Pass data to modern Pipeline ---
        df = new_data.copy()
        
        # --- Step 3: Train a fresh model ---
        new_model = Model()
        report = new_model.train(df, target_column=target_column, categorical_columns=self.categorical_columns)

        # --- Step 4: Save the new model to disk ---
        # Ask the registry what version number will be assigned next.
        # This ensures the file path and DB version always match — even for rejected models.
        next_version = self.registry.get_next_version()
        model_path = f"{self.models_dir}/v{next_version}.pkl"
        new_model.save(model_path)

        # --- Step 5: Register it in the registry (not active yet) ---
        record = self.registry.register(
            path=model_path,
            f1_score=report.f1_score,
            feature_importance=report.feature_importance
        )

        # --- Step 6: Compare and decide whether to promote ---
        if report.f1_score >= old_f1:
            # New model is better — promote it
            self.registry.set_active(record.version)
            return RetrainResult(
                promoted=True,
                old_version=old_version,
                new_version=record.version,
                old_f1=old_f1,
                new_f1=report.f1_score,
                reason=f"New model F1 {report.f1_score} >= old F1 {old_f1}. Promoted."
            )
        else:
            # New model is worse or equal — reject it, keep current active
            return RetrainResult(
                promoted=False,
                old_version=old_version,
                new_version=record.version,
                old_f1=old_f1,
                new_f1=report.f1_score,
                reason=f"New model F1 {report.f1_score} <= old F1 {old_f1}. Rejected."
            )