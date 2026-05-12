"""Datasets endpoint — Day 2/3 of sprint."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from liulian_api.routers.experiments import Page

router = APIRouter(prefix='/datasets', tags=['datasets'])


class DatasetCard(BaseModel):
    id: str
    name: str
    manifest_path: str
    n_stations: int
    n_features: int
    horizon_hours: int
    span_start: datetime
    span_end: datetime
    integrity_hash: str
    description: str | None = None


class DatasetPreview(BaseModel):
    dataset_id: str
    fields: list[dict[str, str]]
    sample_rows: list[dict[str, str | float | None]]
    summary: dict[str, dict[str, float]]


_CATALOG: list[DatasetCard] = [
    DatasetCard(
        id='swiss-river-1990',
        name='Swiss-River 1990',
        manifest_path='manifests/swiss_river/swiss-river-1990.yaml',
        n_stations=28,
        n_features=5,
        horizon_hours=168,
        span_start=datetime(1989, 1, 1, tzinfo=timezone.utc),
        span_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
        integrity_hash='sha256:7af1c2d…',
        description='Discharge + temperature + precipitation across 28 Swiss river stations.',
    ),
    DatasetCard(
        id='swiss-river-2010',
        name='Swiss-River 2010',
        manifest_path='manifests/swiss_river/swiss-river-2010.yaml',
        n_stations=45,
        n_features=5,
        horizon_hours=168,
        span_start=datetime(2010, 1, 1, tzinfo=timezone.utc),
        span_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
        integrity_hash='sha256:a3f0…',
        description='Extended station coverage post-2010, including high-altitude additions.',
    ),
    DatasetCard(
        id='electricity',
        name='Electricity Load (UCI)',
        manifest_path='manifests/electricity.yaml',
        n_stations=321,
        n_features=1,
        horizon_hours=96,
        span_start=datetime(2012, 1, 1, tzinfo=timezone.utc),
        span_end=datetime(2014, 12, 31, tzinfo=timezone.utc),
        integrity_hash='sha256:bb12…',
    ),
    DatasetCard(
        id='etth1',
        name='ETT-h1 (Electricity Transformer)',
        manifest_path='manifests/etth1.yaml',
        n_stations=1,
        n_features=7,
        horizon_hours=720,
        span_start=datetime(2016, 7, 1, tzinfo=timezone.utc),
        span_end=datetime(2018, 6, 26, tzinfo=timezone.utc),
        integrity_hash='sha256:c8e2…',
    ),
    DatasetCard(
        id='traffic',
        name='PEMS-Bay Traffic',
        manifest_path='manifests/traffic.yaml',
        n_stations=325,
        n_features=1,
        horizon_hours=24,
        span_start=datetime(2017, 1, 1, tzinfo=timezone.utc),
        span_end=datetime(2017, 5, 31, tzinfo=timezone.utc),
        integrity_hash='sha256:11ee…',
    ),
]


@router.get('', response_model=Page[DatasetCard])
async def list_datasets(page: int = 1, page_size: int = 50) -> Page[DatasetCard]:
    total = len(_CATALOG)
    start = (page - 1) * page_size
    return Page(items=_CATALOG[start : start + page_size], total=total, page=page, page_size=page_size)


@router.get('/{dataset_id}', response_model=DatasetCard)
async def get_dataset(dataset_id: str) -> DatasetCard:
    for d in _CATALOG:
        if d.id == dataset_id:
            return d
    raise HTTPException(
        status_code=404,
        detail={'code': 'not_found', 'message': f'dataset {dataset_id!r} not registered', 'details': {}},
    )


@router.get('/{dataset_id}/preview', response_model=DatasetPreview)
async def preview_dataset(dataset_id: str, n_rows: int = 5) -> DatasetPreview:
    """Day-1 stub: returns plausible-shaped preview rows."""
    for d in _CATALOG:
        if d.id == dataset_id:
            fields = [
                {'name': 'timestamp', 'dtype': 'datetime64[ns, UTC]'},
                {'name': 'station_id', 'dtype': 'category'},
                {'name': 'discharge_m3s', 'dtype': 'float32'},
                {'name': 'temperature_c', 'dtype': 'float32'},
                {'name': 'precipitation_mm', 'dtype': 'float32'},
            ]
            sample_rows: list[dict[str, str | float | None]] = []
            for i in range(min(n_rows, 5)):
                sample_rows.append({
                    'timestamp': (datetime(2024, 5, 1, tzinfo=timezone.utc).isoformat()),
                    'station_id': f'aare-bern',
                    'discharge_m3s': 408.2 + i * 4.1,
                    'temperature_c': 12.4 - i * 0.3,
                    'precipitation_mm': 1.2 if i == 0 else None,
                })
            return DatasetPreview(
                dataset_id=dataset_id,
                fields=fields,
                sample_rows=sample_rows,
                summary={
                    'discharge_m3s': {'mean': 410.5, 'std': 88.2, 'min': 120.0, 'max': 1240.0},
                    'temperature_c': {'mean': 8.7, 'std': 6.1, 'min': -3.2, 'max': 22.4},
                },
            )
    raise HTTPException(
        status_code=404,
        detail={'code': 'not_found', 'message': f'dataset {dataset_id!r} not registered', 'details': {}},
    )
