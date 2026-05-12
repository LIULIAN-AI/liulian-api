"""Forecasts endpoint — Day 2 of sprint.

Returns forecast objects with prediction intervals (Q05–Q95). The shape
is the canonical TS/ST product surface; web `<ForecastChart />`
(PLATFORM_DESIGN.md §4.2) consumes this directly.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from liulian_api.routers.experiments import Page

router = APIRouter(prefix='/forecasts', tags=['forecasts'])


class ForecastSeries(BaseModel):
    """One forecast for one station, one model, one horizon."""

    id: uuid.UUID
    model_id: str
    dataset_id: str
    station_id: str
    horizon_hours: int
    forecast_at: datetime
    timestamps: list[datetime]
    observed: list[float | None]
    mean: list[float]
    q05: list[float]
    q95: list[float]
    units: str = 'm³/s'


def _synth_fan(seed: int, horizon: int, base: float, slope: float, noise: float) -> dict[str, list]:
    """Produce a deterministic fake forecast for Day-1 stub.

    Day 3 swaps this for real Chronos-2 + adapter-routed forecasts from
    the liulian-core registry.
    """
    rng = (seed * 1103515245 + 12345) % (1 << 31)

    def jitter(i: int, scale: float) -> float:
        nonlocal rng
        rng = (rng * 1103515245 + 12345) % (1 << 31)
        return (rng / (1 << 31) - 0.5) * scale

    mean = [base + slope * i + jitter(i, noise) for i in range(horizon)]
    width = [noise * (1 + i / horizon) * 1.96 for i in range(horizon)]
    return {
        'mean': mean,
        'q05': [m - w for m, w in zip(mean, width)],
        'q95': [m + w for m, w in zip(mean, width)],
    }


def _build_demo_forecast(station_id: str, model_id: str, base: float) -> ForecastSeries:
    horizon = 72
    now = datetime(2026, 5, 12, 14, 38, tzinfo=timezone.utc)
    timestamps = [now + timedelta(hours=i) for i in range(horizon)]
    observed = [base + math.sin(i / 6) * 12 if i < 24 else None for i in range(horizon)]
    fan = _synth_fan(seed=hash((station_id, model_id)) & 0xFFFF, horizon=horizon, base=base, slope=0.4, noise=8.5)
    return ForecastSeries(
        id=uuid.uuid5(uuid.NAMESPACE_OID, f'forecast-{station_id}-{model_id}'),
        model_id=model_id,
        dataset_id='swiss-river-1990',
        station_id=station_id,
        horizon_hours=horizon,
        forecast_at=now,
        timestamps=timestamps,
        observed=observed,
        mean=fan['mean'],
        q05=fan['q05'],
        q95=fan['q95'],
    )


_DEMO_FORECASTS: list[ForecastSeries] = [
    _build_demo_forecast('aare-bern', 'patchtst', 408.2),
    _build_demo_forecast('aare-bern', 'chronos-2', 408.2),
    _build_demo_forecast('aare-thun', 'patchtst', 312.7),
    _build_demo_forecast('rhine-basel', 'patchtst', 1024.5),
    _build_demo_forecast('reuss-luzern', 'patchtst', 198.3),
]


@router.get('', response_model=Page[ForecastSeries])
async def list_forecasts(
    station_id: str | None = None,
    model_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> Page[ForecastSeries]:
    items = _DEMO_FORECASTS
    if station_id:
        items = [f for f in items if f.station_id == station_id]
    if model_id:
        items = [f for f in items if f.model_id == model_id]
    total = len(items)
    start = (page - 1) * page_size
    return Page(items=items[start : start + page_size], total=total, page=page, page_size=page_size)


@router.get('/{forecast_id}', response_model=ForecastSeries)
async def get_forecast(forecast_id: uuid.UUID) -> ForecastSeries:
    for f in _DEMO_FORECASTS:
        if f.id == forecast_id:
            return f
    raise HTTPException(
        status_code=404,
        detail={'code': 'not_found', 'message': f'forecast {forecast_id} not found', 'details': {}},
    )
