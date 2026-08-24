from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.app.api.harness_routes import health_router, router as harness_router
from services.api.app.application.harness_runtime import build_harness_runtime
from services.api.app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # The current product surface is the read-only FORTE Harness planning
    # slice. It owns no legacy workspace, task, conversation, or demo store.
    app.state.harness_runtime = build_harness_runtime(settings)
    app.state.checkpoint_backend = "memory"
    app.state.task_store_backend = "memory"
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Office Agent Harness API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(harness_router)
    app.include_router(health_router)
    return app


app = create_app()
