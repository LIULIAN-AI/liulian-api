"""Health endpoints, modelled on Spring Actuator (ADR 0009 §A)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request, status
from pydantic import BaseModel

from liulian_api import __version__

router = APIRouter(tags=['health'])


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float


class ReadyResponse(BaseModel):
    status: str
    version: str
    checks: dict[str, str]


@router.get('/healthz', response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def healthz(request: Request) -> HealthResponse:
    """Liveness — the process is up. Cheap; does not touch DB."""
    started_at: float = getattr(request.app.state, 'started_at', time.time())
    return HealthResponse(
        status='ok',
        version=__version__,
        uptime_seconds=round(time.time() - started_at, 3),
    )


@router.get('/readyz', response_model=ReadyResponse)
async def readyz() -> ReadyResponse:
    """Readiness — dependencies (DB, Redis, MinIO) are reachable.

    Day-1 stub: returns ok unconditionally. M1 will add real ping checks.
    """
    checks: dict[str, str] = {
        'database': 'not-checked-yet',
        'redis': 'not-checked-yet',
        'minio': 'not-checked-yet',
    }
    return ReadyResponse(
        status='ok',
        version=__version__,
        checks=checks,
    )
