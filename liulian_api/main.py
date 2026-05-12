"""liulian-api FastAPI entrypoint.

Sprint Day 1 scope:
  - /healthz + /readyz (liveness + readiness, per actuator pattern in ADR 0009)
  - /models — discovery endpoint listing adapters registered on the
    liulian-python research core. No auth in Day 1.

Subsequent days add /experiments, /forecasts, /datasets, /agents/{name}/invoke,
/reports, etc. See PLATFORM_BLUEPRINT.md §5.2 for the v1 API surface.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from liulian_api import __version__
from liulian_api.config import get_settings
from liulian_api.routers import health, models

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info('liulian-api boot: env=%s, version=%s', settings.env, __version__)
    app.state.started_at = time.time()
    yield
    logger.info('liulian-api shutdown')


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title='liulian-api',
        description=(
            'HTTP gateway over the LIULIAN research core. '
            'OpenAPI is the source-of-truth for liulian-web + liulian-mobile + liulian-sdk codegen.'
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url='/api/docs',
        redoc_url='/api/redoc',
        openapi_url='/api/openapi.json',
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    app.include_router(health.router)
    app.include_router(models.router)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Any, exc: Exception) -> JSONResponse:
        # RFC-7807-ish error envelope (per ADR 0009)
        logger.exception('unhandled: %s', exc)
        return JSONResponse(
            status_code=500,
            content={
                'code': 'internal_error',
                'message': 'Internal server error',
                'details': {'type': type(exc).__name__},
            },
        )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        'liulian_api.main:app',
        host='0.0.0.0',
        port=8000,
        reload=True,
        log_level='info',
    )


if __name__ == '__main__':
    main()
