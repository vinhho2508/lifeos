from fastapi import Request, status
from fastapi.responses import JSONResponse
from src.core.logging import logger

class LifeOSError(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

async def lifeos_exception_handler(request: Request, exc: LifeOSError):
    logger.error(f"Error: {exc.message} at {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )
