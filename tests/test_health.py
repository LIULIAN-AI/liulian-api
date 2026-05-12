"""Smoke tests for the Day-1 endpoints. No real DB; FastAPI's TestClient only."""

from __future__ import annotations

from fastapi.testclient import TestClient

from liulian_api.main import app


def test_healthz() -> None:
    with TestClient(app) as client:
        r = client.get('/healthz')
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'ok'
    assert isinstance(body['version'], str)
    assert isinstance(body['uptime_seconds'], (int, float))


def test_readyz() -> None:
    with TestClient(app) as client:
        r = client.get('/readyz')
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'ok'
    assert 'checks' in body


def test_list_models() -> None:
    with TestClient(app) as client:
        r = client.get('/models')
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 20  # 20+ liulian-core models + planned externals
    # Verify expected families present
    families = {m['family'] for m in items}
    assert {
        'classical',
        'decomposition',
        'efficient',
        'patch',
        'mixture',
        'state-space',
        'foundation',
    } <= families


def test_list_models_filter() -> None:
    with TestClient(app) as client:
        r = client.get('/models', params={'family': 'patch'})
    assert r.status_code == 200
    items = r.json()
    assert all(m['family'] == 'patch' for m in items)
    assert any(m['id'] == 'patchtst' for m in items)


def test_get_model_by_id() -> None:
    with TestClient(app) as client:
        r = client.get('/models/patchtst')
    assert r.status_code == 200
    assert r.json()['id'] == 'patchtst'


def test_get_model_not_found() -> None:
    with TestClient(app) as client:
        r = client.get('/models/this-model-does-not-exist')
    assert r.status_code == 404
    assert r.json()['detail']['code'] == 'not_found'
