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
from services.api.app.application.task_storage import InMemoryTaskStore, PostgresTaskStore
from services.api.app.application.tasks import TaskService
from services.api.app.application.task_stage_agent import AutoDLTaskStageAgent
from services.api.app.application.demo2_cockpit import Demo2CockpitService
from services.api.app.application.demo2_execution import DeepSeekDemo2WorkerAgent, Demo2ExecutionService
from services.api.app.application.conversations import ConversationService
from services.api.app.config import get_settings


def _build_task_service(task_store, settings):
    """Inject the single strict Task Stage agent used by the progressive runtime."""
    stage_agent = AutoDLTaskStageAgent(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
        thinking_mode=settings.llm_thinking_mode,
    )
    return TaskService(task_store, stage_agent=stage_agent)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    task_store_dsn = settings.database_dsn or settings.langgraph_checkpoint_dsn
    if task_store_dsn:
        task_store = PostgresTaskStore(task_store_dsn)
        app.state.task_store_backend = "postgres"
    else:
        task_store = InMemoryTaskStore()
        app.state.task_store_backend = "memory"
    await task_store.setup()
    app.state.task_service = _build_task_service(task_store, settings)
    # Demo 2 is an in-memory controlled execution slice; process restart discards it.
    app.state.demo2_cockpit_service = Demo2CockpitService()
    await app.state.demo2_cockpit_service.setup()
    app.state.demo2_execution_service = Demo2ExecutionService(
        app.state.demo2_cockpit_service,
        worker_agent=DeepSeekDemo2WorkerAgent(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        ),
    )
    await app.state.demo2_execution_service.setup()

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
            app.state.run_service.attach_task_artifact_validator(
                app.state.task_service.validate_action_binding
            )
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
        app.state.run_service.attach_task_artifact_validator(
            app.state.task_service.validate_action_binding
        )
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
