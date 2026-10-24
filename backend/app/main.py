from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    deadline,
    documents,
    evaluate,
    health,
    packet,
    rules,
    samples,
    timeline,
    validate,
)
from app.errors import ApiError
from app.rules.loader import get_rules
from app.settings import get_settings

# Routers are added here as later steps implement them (all under /api).
ROUTERS: list[APIRouter] = [
    health.router,
    rules.router,
    samples.router,
    documents.router,
    validate.router,
    evaluate.router,
    packet.router,
    timeline.router,
    deadline.router,
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Load and validate rules once; RulesError (naming the rule id) stops startup.
    get_rules()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Proofline API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    for router in ROUTERS:
        app.include_router(router, prefix="/api")

    settings.samples_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/samples", StaticFiles(directory=settings.samples_dir), name="samples")

    dist = settings.frontend_dist
    if dist.is_dir():
        dist_root = dist.resolve()
        index_file = dist_root / "index.html"

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str) -> FileResponse:
            if full_path.startswith(("api/", "samples/")) or full_path in ("api", "samples"):
                raise HTTPException(status_code=404)
            candidate = (dist_root / full_path).resolve()
            if full_path and candidate.is_file() and candidate.is_relative_to(dist_root):
                return FileResponse(candidate)
            return FileResponse(index_file)

    return app


app = create_app()
