from dataclasses import dataclass
from core.drift import DriftReport

from config import MIN_F1_THRESHOLD, DRIFT_RETRAIN_THRESHOLD, DRIFT_ALERT_THRESHOLD

@dataclass
class HealerDecision:
    """The output of the healer — what action to take and why."""
    action: str          # "retrain" | "rollback" | "alert" | "none"
    reason: str          # human-readable explanation
    drifted_features: list[str]  # which features triggered the decision


class Healer:
    def __init__(
        self,
        min_f1: float = MIN_F1_THRESHOLD,
        drift_retrain: float = DRIFT_RETRAIN_THRESHOLD,
        drift_alert: float = DRIFT_ALERT_THRESHOLD
    ):
        # Thresholds are injectable so we can tune them later without changing this file
        self.min_f1 = min_f1
        self.drift_retrain = drift_retrain
        self.drift_alert = drift_alert

    def decide(
        self,
        drift_reports: dict[str, DriftReport],
        current_f1: float
    ) -> HealerDecision:
        """
        Takes drift reports and current F1, returns a decision.

        Decision priority order matters:
        1. Check model performance first — if F1 is bad, rollback immediately.
           No point retraining on drifted data if the model is already broken.
        2. Check for severe drift → retrain.
        3. Check for mild drift → alert.
        4. If nothing is wrong → none.
        """

        # --- Step 1: Check model performance ---
        # If F1 dropped below the minimum threshold, the model is too unreliable.
        # Retraining won't help here because we don't know why it's bad yet.
        # Safest action: rollback to last known good version.
        if current_f1 < self.min_f1:
            return HealerDecision(
                action="rollback",
                reason=f"F1 score {current_f1} dropped below minimum threshold {self.min_f1}",
                drifted_features=[]
            )

        # --- Step 2: Find which features have drifted ---
        # Separate features into "severe drift" and "mild drift" buckets
        severe = []   # PSI above drift_retrain threshold → needs retraining
        mild = []     # PSI above drift_alert threshold → worth flagging

        for feature, report in drift_reports.items():
            if report.psi_score >= self.drift_retrain:
                severe.append(feature)
            elif report.psi_score >= self.drift_alert:
                mild.append(feature)

        # --- Step 3: Severe drift → retrain ---
        # Data has shifted enough that the model's training distribution no longer
        # matches what it's seeing. It needs to learn from new data.
        if severe:
            return HealerDecision(
                action="retrain",
                reason=f"Severe drift detected in: {', '.join(severe)}",
                drifted_features=severe
            )

        # --- Step 4: Mild drift → alert ---
        # Not bad enough to act yet, but worth flagging.
        # A human should be aware this is happening.
        if mild:
            return HealerDecision(
                action="alert",
                reason=f"Mild drift detected in: {', '.join(mild)}",
                drifted_features=mild
            )

        # --- Step 5: Everything looks fine ---
        return HealerDecision(
            action="none",
            reason="No drift detected and model performance is acceptable",
            drifted_features=[]
        )