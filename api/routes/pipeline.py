# API routes for pipeline lifecycle control

from fastapi import APIRouter
from api import runner
from api.state import pipeline_state
from api.schemas import PipelineStatusResponse, ActionResponse

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

from adapters.fraud import FraudAdapter

@router.post("/start", response_model=ActionResponse)
def start_pipeline(scenario: str = "normal"):
    adapter = FraudAdapter(scenario=scenario)
    started = runner.start(adapter=adapter)
    if started:
        return ActionResponse(success=True, message=f"Pipeline started with scenario='{scenario}'")
    return ActionResponse(success=False, message="Pipeline is already running")

@router.post("/stop", response_model=ActionResponse)
def stop_pipeline():
    runner.stop()
    return ActionResponse(success=True, message="Stop signal sent")

@router.get("/status", response_model=PipelineStatusResponse)
def get_status():
    return PipelineStatusResponse(**pipeline_state.snapshot())
