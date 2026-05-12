"""Alerts endpoints: rules + fired events."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from liulian_api.routers.experiments import Page

router = APIRouter(prefix='/alerts', tags=['alerts'])


class AlertExpr(BaseModel):
    kind: str = Field('threshold', pattern='^(threshold|anomaly)$')
    field: str  # 'mean' | 'q05' | 'q95' | 'observation'
    operator: str  # '>' | '>=' | '<' | '<=' | 'between'
    value: float
    value_upper: float | None = None


class AlertChannel(BaseModel):
    type: str  # 'email' | 'slack' | 'webhook'
    target: str


class AlertRuleCreate(BaseModel):
    name: str
    expr: AlertExpr
    station_id: str | None = None
    model_id: str | None = None
    severity: str = Field('elevated', pattern='^(watch|elevated|critical)$')
    channel: AlertChannel | None = None


class AlertRuleRead(AlertRuleCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime


class AlertEvent(BaseModel):
    id: uuid.UUID
    rule_id: uuid.UUID
    rule_name: str
    severity: str
    station_id: str | None
    fired_at: datetime
    forecast_id: uuid.UUID | None
    payload: dict[str, float | str]


_DEMO_TENANT = uuid.UUID('00000000-0000-0000-0000-000000000001')


def _seed() -> tuple[dict[uuid.UUID, AlertRuleRead], list[AlertEvent]]:
    rules: dict[uuid.UUID, AlertRuleRead] = {}
    for ix, (name, station, severity, value) in enumerate([
        ('Bern Q95 elevated', 'aare-bern', 'elevated', 850.0),
        ('Bern Q95 critical', 'aare-bern', 'critical', 1200.0),
        ('Basel watch', 'rhine-basel', 'watch', 1500.0),
    ]):
        rid = uuid.uuid5(uuid.NAMESPACE_OID, f'rule-{name}')
        rules[rid] = AlertRuleRead(
            id=rid,
            tenant_id=_DEMO_TENANT,
            name=name,
            expr=AlertExpr(kind='threshold', field='q95', operator='>', value=value),
            station_id=station,
            severity=severity,
            channel=None,
            created_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        )

    events: list[AlertEvent] = []
    base = datetime(2026, 5, 9, 8, 0, tzinfo=timezone.utc)
    # 3 firing windows for each rule, staggered
    for ri, (rid, rule) in enumerate(rules.items()):
        for j in range(3):
            evt_t = base + timedelta(hours=ri * 6 + j * 30)
            events.append(AlertEvent(
                id=uuid.uuid4(),
                rule_id=rid,
                rule_name=rule.name,
                severity=rule.severity,
                station_id=rule.station_id,
                fired_at=evt_t,
                forecast_id=None,
                payload={'q95_observed': rule.expr.value + 18.0 * (j + 1), 'threshold': rule.expr.value},
            ))
    return rules, events


_RULES, _EVENTS = _seed()


@router.get('/rules', response_model=Page[AlertRuleRead])
async def list_rules(page: int = 1, page_size: int = 50) -> Page[AlertRuleRead]:
    items = list(_RULES.values())
    total = len(items)
    start = (page - 1) * page_size
    return Page(items=items[start : start + page_size], total=total, page=page, page_size=page_size)


@router.post('/rules', response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(body: AlertRuleCreate) -> AlertRuleRead:
    rid = uuid.uuid4()
    rule = AlertRuleRead(
        id=rid,
        tenant_id=_DEMO_TENANT,
        name=body.name,
        expr=body.expr,
        station_id=body.station_id,
        model_id=body.model_id,
        severity=body.severity,
        channel=body.channel,
        created_at=datetime.now(timezone.utc),
    )
    _RULES[rid] = rule
    return rule


@router.delete('/rules/{rule_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: uuid.UUID) -> None:
    if rule_id not in _RULES:
        raise HTTPException(
            status_code=404,
            detail={'code': 'not_found', 'message': 'rule not found', 'details': {}},
        )
    del _RULES[rule_id]


@router.get('/events', response_model=Page[AlertEvent])
async def list_events(
    severity: str | None = None,
    station_id: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> Page[AlertEvent]:
    items = _EVENTS
    if severity:
        items = [e for e in items if e.severity == severity]
    if station_id:
        items = [e for e in items if e.station_id == station_id]
    total = len(items)
    start = (page - 1) * page_size
    return Page(items=items[start : start + page_size], total=total, page=page, page_size=page_size)
