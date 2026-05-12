"""Experiments endpoint — Day 2 of sprint.

Sprint Day 2: CRUD over experiments. Day 1 already shipped /models;
this adds /experiments + /experiments/{id} + /experiments/{id}/run.

Per ADR 0009, the pagination contract is `{items, total, page, page_size}`
and the error envelope is `{code, message, details}` — both inherited
verbatim from neobanker-backend-MVP-V2.

Storage on Day 1: in-memory dict; Day 2 sprint adds SQLModel + Postgres
+ Alembic migration. Storage swap is a single file change; the API
surface is stable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generic, TypeVar

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(prefix='/experiments', tags=['experiments'])

T = TypeVar('T')


class Page(BaseModel, Generic[T]):
    """Pagination envelope, mirrors neobanker contract verbatim (ADR 0009)."""

    items: list[T]
    total: int
    page: int = 1
    page_size: int = 50


class ExperimentRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    model_id: str
    dataset_id: str
    config_yaml: str | None = None
    status: str  # 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'aborted'
    liulian_version: str = '0.0.1'
    created_at: datetime
    completed_at: datetime | None = None


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    model_id: str
    dataset_id: str
    config_yaml: str | None = None


# Day 1 in-memory store; Day 2 swaps to SQLModel + Postgres.
_STORE: dict[uuid.UUID, ExperimentRead] = {}
_DEMO_TENANT = uuid.UUID('00000000-0000-0000-0000-000000000001')


def _seed_demo() -> None:
    """Seed two SwissRiver-shaped demo rows so /experiments isn't empty on cold start."""
    if _STORE:
        return
    for ix, (model, status_) in enumerate([
        ('lstm', 'completed'),
        ('patchtst', 'running'),
        ('chronos-2', 'pending'),
    ]):
        eid = uuid.uuid5(uuid.NAMESPACE_OID, f'demo-{model}-{ix}')
        _STORE[eid] = ExperimentRead(
            id=eid,
            tenant_id=_DEMO_TENANT,
            name=f'swiss-river-1990 / {model} / entity=none',
            model_id=model,
            dataset_id='swiss-river-1990',
            status=status_,
            created_at=datetime(2026, 5, 12, 14, 38, tzinfo=timezone.utc),
            completed_at=datetime(2026, 5, 12, 15, 12, tzinfo=timezone.utc) if status_ == 'completed' else None,
        )


_seed_demo()


@router.get('', response_model=Page[ExperimentRead])
async def list_experiments(
    status_filter: str | None = Query(None, alias='status'),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[ExperimentRead]:
    items = list(_STORE.values())
    if status_filter:
        items = [x for x in items if x.status == status_filter]
    total = len(items)
    start = (page - 1) * page_size
    return Page(items=items[start : start + page_size], total=total, page=page, page_size=page_size)


@router.get('/{experiment_id}', response_model=ExperimentRead)
async def get_experiment(experiment_id: uuid.UUID) -> ExperimentRead:
    if experiment_id not in _STORE:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 'not_found',
                'message': f'experiment {experiment_id} not found',
                'details': {},
            },
        )
    return _STORE[experiment_id]


@router.post('', response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
async def create_experiment(body: ExperimentCreate) -> ExperimentRead:
    eid = uuid.uuid4()
    exp = ExperimentRead(
        id=eid,
        tenant_id=_DEMO_TENANT,
        name=body.name,
        model_id=body.model_id,
        dataset_id=body.dataset_id,
        config_yaml=body.config_yaml,
        status='pending',
        created_at=datetime.now(timezone.utc),
    )
    _STORE[eid] = exp
    return exp


@router.post('/{experiment_id}/run', status_code=status.HTTP_202_ACCEPTED)
async def run_experiment(experiment_id: uuid.UUID) -> dict[str, str]:
    """Trigger training. Day 1 stub: just flips status. Day 5 wires arq workers."""
    if experiment_id not in _STORE:
        raise HTTPException(
            status_code=404,
            detail={'code': 'not_found', 'message': 'experiment not found', 'details': {}},
        )
    exp = _STORE[experiment_id]
    if exp.status not in ('pending', 'failed'):
        raise HTTPException(
            status_code=409,
            detail={
                'code': 'conflict',
                'message': f'cannot run experiment in status {exp.status}',
                'details': {'current_status': exp.status},
            },
        )
    _STORE[experiment_id] = exp.model_copy(update={'status': 'queued'})
    return {'status': 'queued', 'experiment_id': str(experiment_id)}
