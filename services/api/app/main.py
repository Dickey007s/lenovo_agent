import asyncio
import sys
from contextlib import asynccontextmanager

# psycopg async connections require a selector event loop on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from packages.audit import PostgresAuditLog
from services.api.app.api.routes import build_run_service, router
from services.api.app.application.storage import (
    InMemoryWorkspaceStore,
    PostgresRunStore,
    PostgresWorkspaceStore,
)
from services.api.app.application.conversations import ConversationService
from services.api.app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.langgraph_checkpoint_dsn:
        database_dsn = settings.database_dsn or settings.langgraph_checkpoint_dsn
        run_store = PostgresRunStore(database_dsn)
        workspace_store = PostgresWorkspaceStore(database_dsn)
        audit_log = PostgresAuditLog(database_dsn)
        await run_store.setup()
        await workspace_store.setup()
        await audit_log.setup()
        async with AsyncPostgresSaver.from_conn_string(
            settings.langgraph_checkpoint_dsn
        ) as checkpointer:
            await checkpointer.setup()
            app.state.run_service = build_run_service(checkpointer, run_store, audit_log)
            await app.state.run_service.restore()
            app.state.conversation_service = ConversationService(
                app.state.run_service.parser,
                app.state.run_service,
                workspace_store,
            )
            app.state.checkpoint_backend = "postgres"
            yield
    else:
        workspace_store = InMemoryWorkspaceStore()
        await workspace_store.setup()
        app.state.run_service = build_run_service(InMemorySaver())
        app.state.conversation_service = ConversationService(
            app.state.run_service.parser,
            app.state.run_service,
            workspace_store,
        )
        app.state.checkpoint_backend = "memory"
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Office Agent P0 API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
