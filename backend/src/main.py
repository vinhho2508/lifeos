from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.core.exceptions import LifeOSError, lifeos_exception_handler
from src.core.logging import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.agent.checkpointer import close_checkpointer, open_checkpointer
    from src.core.migrations import run_migrations

    await run_migrations()
    await open_checkpointer()

    # Import to trigger @cron_service.register decorators, then start scheduler
    from src.services import cron_jobs  # noqa: F401
    from src.services.cron_service import cron_service

    cron_service.start()
    yield
    await close_checkpointer()


app = FastAPI(title="LifeOS Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(LifeOSError, lifeos_exception_handler)
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Welcome to LifeOS Assistant API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
