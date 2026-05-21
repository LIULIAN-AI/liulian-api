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

from liulian_api.data import swiss_river as _sr
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
    units: str = '°C'
    # Real-data flag — set True when the observed series comes from the
    # swiss-1990 CSV; False when fully synthetic (legacy demo IDs).
    real_data: bool = False


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


def _build_real_forecast(station_id: str, model_id: str) -> ForecastSeries | None:
    """Try to build a forecast from real swiss-river-1990 CSV.

    Schema:
      observed = last 28 daily water-temperature values from the CSV
      forecast = next 14 daily steps by linear extrapolation of last 14 obs
      timestamps = day-aligned, starting at the last real observation
    """
    try:
        series = _sr.station_series('swiss-1990', station_id, 'wt')
    except (KeyError, FileNotFoundError):
        return None

    clean = [(t, v) for t, v in zip(series.timestamps, series.values) if v is not None]
    if len(clean) < 14:
        return None

    obs_window = clean[-28:]
    obs_timestamps = [t for t, _ in obs_window]
    obs_values = [v for _, v in obs_window]
    last_t = obs_timestamps[-1]

    horizon = 14
    future_ts = [last_t + timedelta(days=i + 1) for i in range(horizon)]
    fan = _sr.synth_forecast(obs_values, horizon=horizon, noise_scale=0.7)

    all_ts = obs_timestamps + future_ts
    all_observed: list[float | None] = list(obs_values) + [None] * horizon
    all_mean: list[float] = list(obs_values) + fan['mean']
    all_q05: list[float] = list(obs_values) + fan['q05']
    all_q95: list[float] = list(obs_values) + fan['q95']

    return ForecastSeries(
        id=uuid.uuid5(uuid.NAMESPACE_OID, f'real-forecast-{station_id}-{model_id}'),
        model_id=model_id,
        dataset_id='swiss-river-1990',
        station_id=station_id,
        horizon_hours=horizon * 24,
        forecast_at=last_t,
        timestamps=all_ts,
        observed=all_observed,
        mean=all_mean,
        q05=all_q05,
        q95=all_q95,
        units='°C',
        real_data=True,
    )


def _build_synth_forecast(station_id: str, model_id: str, base: float) -> ForecastSeries:
    """Synthetic fallback for legacy demo station ids."""
    horizon = 72
    real_now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    forecast_at = real_now
    timestamps = [real_now + timedelta(hours=i - 24) for i in range(horizon)]
    observed = [base + math.sin(i / 6) * 12 if i < 24 else None for i in range(horizon)]
    fan = _synth_fan(seed=hash((station_id, model_id)) & 0xFFFF, horizon=horizon, base=base, slope=0.4, noise=8.5)
    return ForecastSeries(
        id=uuid.uuid5(uuid.NAMESPACE_OID, f'forecast-{station_id}-{model_id}'),
        model_id=model_id,
        dataset_id='swiss-river-1990',
        station_id=station_id,
        horizon_hours=horizon,
        forecast_at=forecast_at,
        timestamps=timestamps,
        observed=observed,
        mean=fan['mean'],
        q05=fan['q05'],
        q95=fan['q95'],
        units='m³/s',
        real_data=False,
    )


def _build_demo_forecast(station_id: str, model_id: str, base: float = 0.0) -> ForecastSeries:
    """Public builder: prefer real CSV data when available, fall back to synthetic."""
    real = _build_real_forecast(station_id, model_id)
    if real is not None:
        return real
    return _build_synth_forecast(station_id, model_id, base)


def _real_station_seed() -> list[tuple[str, str, float]]:
    """Pick the first 5 real swiss-1990 stations for the default panel set.

    Returns (station_id, model_id, unused-base) triples — base only used
    on the synthetic fallback path.
    """
    try:
        stations = _sr.list_stations('swiss-1990')
    except FileNotFoundError:
        stations = []
    if not stations:
        # Legacy demo fallback for when the swiss CSV directory is missing.
        return [
            ('aare-bern', 'patchtst', 408.2),
            ('aare-bern', 'chronos-2', 408.2),
            ('aare-thun', 'patchtst', 312.7),
            ('rhine-basel', 'patchtst', 1024.5),
            ('reuss-luzern', 'patchtst', 198.3),
        ]
    out: list[tuple[str, str, float]] = []
    for sid in stations[:5]:
        out.append((sid, 'patchtst', 0.0))
    # Add chronos-2 for the first station so the multi-model overlay has 2+ series
    out.append((stations[0], 'chronos-2', 0.0))
    return out


def _build_demo_forecasts() -> list[ForecastSeries]:
    return [_build_demo_forecast(s, m, b) for s, m, b in _real_station_seed()]


@router.get('', response_model=Page[ForecastSeries])
async def list_forecasts(
    station_id: str | None = None,
    model_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> Page[ForecastSeries]:
    # When a specific station is requested, build forecasts for it on-demand.
    # The seed list is only the "default canvas set" for unfiltered queries.
    if station_id:
        wanted_models = [model_id] if model_id else ['patchtst', 'chronos-2']
        items = [_build_demo_forecast(station_id, m) for m in wanted_models]
    else:
        items = _build_demo_forecasts()
        if model_id:
            items = [f for f in items if f.model_id == model_id]
    total = len(items)
    start = (page - 1) * page_size
    return Page(items=items[start : start + page_size], total=total, page=page, page_size=page_size)


@router.get('/{forecast_id}', response_model=ForecastSeries)
async def get_forecast(forecast_id: uuid.UUID) -> ForecastSeries:
    for f in _build_demo_forecasts():
        if f.id == forecast_id:
            return f
    raise HTTPException(
        status_code=404,
        detail={'code': 'not_found', 'message': f'forecast {forecast_id} not found', 'details': {}},
    )
