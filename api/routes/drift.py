# on-demand drift check

from fastapi import APIRouter
from adapters.fraud import FraudAdapter
from core.drift import calculate_drift
from api.schemas import DriftReportResponse, DriftFeatureReport

router = APIRouter(prefix="/drift", tags=["Drift"])

@router.get("/check", response_model=DriftReportResponse)
def check_drift(scenario: str = "normal"):
    adapter = FraudAdapter(scenario=scenario)
    baseline = adapter.load_baseline()
    current = adapter.get_current_data()
    
    # Drop target — we never have labels on live incoming data
    reports = calculate_drift(
        baseline.drop(columns=[adapter.target_column]),
        current.drop(columns=[adapter.target_column]),
        categorical_columns=adapter.categorical_columns
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
