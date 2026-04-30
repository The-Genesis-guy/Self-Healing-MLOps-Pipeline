# Pydantic models for API request/response validation

from pydantic import BaseModel
from typing import Optional

class PipelineStatusResponse(BaseModel):
    running: bool
    iteration: int
    last_action: str
    last_reason: str
    last_drifted_features: list[str]
    active_model_version: Optional[int]
    active_model_f1: Optional[float]

class ModelResponse(BaseModel):
    version: int
    path: str
    accuracy: float
    f1_score: float
    trained_at: str
    is_active: bool

class DriftFeatureReport(BaseModel):
    feature: str
    psi_score: float
    drifted: bool

class DriftReportResponse(BaseModel):
    scenario: str
    features: list[DriftFeatureReport]

class ActionResponse(BaseModel):
    success: bool
    message: str
