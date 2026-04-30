# on-demand drift check

from fastapi import APIRouter
from adapters.fraud import load_baseline, simulate_drift, CATEGORICAL_COLUMNS, TARGET_COLUMN
from core.drift import calculate_drift
from api.schemas import DriftReportResponse, DriftFeatureReport

router = APIRouter(prefix="/drift", tags=["Drift"])

@router.get("/check", response_model=DriftReportResponse)
def check_drift(scenario: str = "normal"):
    baseline = load_baseline()
    current = simulate_drift(baseline, scenario)
    # Drop target — we never have labels on live incoming data
    reports = calculate_drift(
        baseline.drop(columns=[TARGET_COLUMN]),
        current.drop(columns=[TARGET_COLUMN]),
        categorical_columns=CATEGORICAL_COLUMNS
    )

    features = [
        DriftFeatureReport(
            feature=name,
            psi_score=report.psi_score,
            drifted=report.drifted
        )
        for name, report in reports.items()
    ]
    return DriftReportResponse(scenario=scenario, features=features)
