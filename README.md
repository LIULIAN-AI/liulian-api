# liulian-api

> **Language:** English | [中文](README.zh.md) *(stub pending)*

HTTP gateway over the LIULIAN research core. FastAPI + Pydantic v2 +
SQLModel + plain Postgres (Day-1 pragmatism per ADR 0003; TimescaleDB
extension after M1 demo ships).

## Quickstart

```bash
# 1. Dev services (plain Postgres, Redis, MinIO)
docker compose -f docker-compose.dev.yml up -d

# 2. Install
uv sync --all-extras

# 3. Run
uv run liulian-api
# or: uv run uvicorn liulian_api.main:app --reload
```

Swagger UI at <http://localhost:8000/api/docs>.

## Endpoints (Day 1)

| Method | Path | Notes |
|---|---|---|
| GET | `/healthz` | Liveness; cheap; doesn't touch DB |
| GET | `/readyz` | Readiness; checks DB / Redis / MinIO (stub on Day 1) |
| GET | `/models` | Lists adapters registered on `liulian-core`. Filters: `family`, `source` |
| GET | `/models/{id}` | One model card |

Coming on Day 2:
`/experiments`, `/forecasts`, `/datasets`, `/agents/{name}/invoke`,
`/reports`, MLflow-compatible tracking shim, audit-log middleware.

## Architecture

See `liulian-python/docs/strategy/PLATFORM_BLUEPRINT.md §5` for the
full backend spec and `adr/0009-spring-boot-to-fastapi-pattern-translation.md`
for the Spring Boot → FastAPI pattern translation.

## Environment

All settings via `LIULIAN_API_*` env vars or `.env`. See
`liulian_api/config.py`. CORS env-var name (`LIULIAN_API_CORS_ALLOWED_ORIGINS`)
mirrors neobanker's convention (ADR 0009).

## License

MIT.
