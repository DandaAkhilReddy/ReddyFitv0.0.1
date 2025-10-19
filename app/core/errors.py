from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def format_error(code: str, message: str):
    return {"error": {"code": code, "message": message}}


async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status, content=format_error(exc.code, exc.message))

