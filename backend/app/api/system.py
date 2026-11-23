"""Phase 1 system and liveness routes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from novaenterprise import __version__

router = APIRouter(tags=["system"])


class ServiceInfo(BaseModel):
    """Public metadata for the running service."""

    name: str
    status: str
    version: str


class LivenessStatus(BaseModel):
    """Minimal process-liveness response."""

    service: str
    status: str


@router.get("/", response_model=ServiceInfo, summary="Describe the service")
def service_info(request: Request) -> ServiceInfo:
    settings = request.app.state.settings
    return ServiceInfo(name=settings.app_name, status="available", version=__version__)


@router.get(
    "/health/live",
    response_model=LivenessStatus,
    summary="Confirm that the API process is alive",
)
def liveness(request: Request) -> LivenessStatus:
    return LivenessStatus(service=request.app.state.settings.app_name, status="ok")
