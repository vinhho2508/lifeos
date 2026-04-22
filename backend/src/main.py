from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.router import api_router
from src.core.exceptions import LifeOSError, lifeos_exception_handler
from src.core.database import engine, Base
from src.core.logging import setup_logging

setup_logging()

app = FastAPI(title="LifeOS Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    from src.models.all_models import User, Task, Document, Message # Import models to register them
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

app.add_exception_handler(LifeOSError, lifeos_exception_handler)
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Welcome to LifeOS Assistant API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
