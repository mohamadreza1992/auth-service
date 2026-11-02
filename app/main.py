from fastapi import FastAPI

from app.api.exception_handlers import (
    app_exception_handler,
    unexpected_exception_handler,
)
from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging

setup_logging()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_exception_handler(
    AppError,
    app_exception_handler,
)

app.add_exception_handler(
    Exception,
    unexpected_exception_handler,
)

app.include_router(api_router)
