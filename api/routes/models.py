# API routes for model management

from fastapi import APIRouter, HTTPException
from adapters.fraud import FraudAdapter
from core.registry import ModelRegistry
from api.schemas import ModelResponse, ActionResponse

router = APIRouter(prefix="/models", tags=["Models"])

def get_registry():
    return ModelRegistry(db_path=FraudAdapter().registry_path)

@router.get("", response_model=list[ModelResponse])
def list_models():
    registry = get_registry()
    return [ModelResponse(**m.__dict__) for m in registry.get_all()]

@router.get("/active", response_model=ModelResponse)
def get_active_model():
    registry = get_registry()
    active = registry.get_active()
    if active is None:
        raise HTTPException(status_code=404, detail="No active model found")
    return ModelResponse(**active.__dict__)

@router.post("/{version}/activate", response_model=ActionResponse)
def activate_model(version: int):
    registry = get_registry()
    model = registry.get_by_version(version)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model v{version} not found")
    registry.set_active(version)
    return ActionResponse(success=True, message=f"Model v{version} is now active")
