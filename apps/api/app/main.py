from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api_v1 import router as api_v1_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, unexpected_error_handler
from app.internal_v1 import router as internal_v1_router
from app.mcp.router import router as mcp_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="KoiCloud Phase 0 backend contract freeze",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, _: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "code": "internal_error",
                "message": "Ruta no encontrada",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    app.include_router(api_v1_router, prefix=settings.api_prefix)
    app.include_router(internal_v1_router, prefix=settings.internal_api_prefix)
    app.include_router(mcp_router, prefix=settings.mcp_prefix)
    return app


app = create_app()
