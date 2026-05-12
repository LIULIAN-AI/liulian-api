"""Reports endpoints — saved BI canvas layouts + share URLs."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from liulian_api.routers.experiments import Page

router = APIRouter(prefix='/reports', tags=['reports'])


class PanelSpec(BaseModel):
    """One panel within a saved report. Mirrors react-mosaic-component nodes."""
    id: str
    kind: str  # 'forecast' | 'map' | 'correlation' | 'alert_ribbon' | 'kpi' | 'multi_model'
    config: dict[str, object]
    layout: dict[str, int | float]  # {x, y, w, h} in grid units


class ReportCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    panels: list[PanelSpec]
    description: str | None = None
    public: bool = False
    filters: dict[str, str | None] = {}


class ReportRead(ReportCreate):
    id: uuid.UUID
    slug: str
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


_DEMO_TENANT = uuid.UUID('00000000-0000-0000-0000-000000000001')
_SLUG_RE = re.compile(r'[^a-z0-9]+')


def _make_slug(name: str) -> str:
    s = _SLUG_RE.sub('-', name.lower()).strip('-')
    return s[:60] or 'report'


_STORE: dict[uuid.UUID, ReportRead] = {}


def _seed_demo() -> None:
    if _STORE:
        return
    rid = uuid.uuid5(uuid.NAMESPACE_OID, 'demo-swissriver-report')
    _STORE[rid] = ReportRead(
        id=rid,
        slug='swiss-river-overview',
        tenant_id=_DEMO_TENANT,
        name='Swiss-River — Overview',
        description='Eight-panel canonical canvas: map, forecasts, KPIs, correlation, alerts.',
        public=True,
        panels=[
            PanelSpec(id='map', kind='map', config={'dataset_id': 'swiss-river-1990'}, layout={'x': 0, 'y': 0, 'w': 6, 'h': 4}),
            PanelSpec(id='forecast', kind='forecast', config={'station_id': 'aare-bern', 'model_id': 'patchtst'}, layout={'x': 6, 'y': 0, 'w': 6, 'h': 4}),
            PanelSpec(id='kpi', kind='kpi', config={}, layout={'x': 0, 'y': 4, 'w': 12, 'h': 1}),
            PanelSpec(id='alerts', kind='alert_ribbon', config={'window': '7d'}, layout={'x': 0, 'y': 5, 'w': 12, 'h': 3}),
        ],
        filters={'dataset_id': 'swiss-river-1990'},
        created_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )


_seed_demo()


@router.get('', response_model=Page[ReportRead])
async def list_reports(page: int = 1, page_size: int = 50) -> Page[ReportRead]:
    items = list(_STORE.values())
    total = len(items)
    start = (page - 1) * page_size
    return Page(items=items[start : start + page_size], total=total, page=page, page_size=page_size)


@router.get('/{slug}', response_model=ReportRead)
async def get_report(slug: str) -> ReportRead:
    for r in _STORE.values():
        if r.slug == slug or str(r.id) == slug:
            return r
    raise HTTPException(
        status_code=404,
        detail={'code': 'not_found', 'message': f'report {slug!r} not found', 'details': {}},
    )


@router.post('', response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(body: ReportCreate) -> ReportRead:
    rid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    base = _make_slug(body.name)
    slug = base
    n = 1
    existing = {r.slug for r in _STORE.values()}
    while slug in existing:
        n += 1
        slug = f'{base}-{n}'

    rep = ReportRead(
        id=rid,
        slug=slug,
        tenant_id=_DEMO_TENANT,
        name=body.name,
        description=body.description,
        public=body.public,
        panels=body.panels,
        filters=body.filters,
        created_at=now,
        updated_at=now,
    )
    _STORE[rid] = rep
    return rep
