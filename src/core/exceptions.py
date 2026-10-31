"""Institute Management System - Application Exception Handlers.
Renders responsive glassmorphism HTML error pages for browser requests and structured JSON for API calls.
"""

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.security import SESSION_COOKIE_NAME, verify_session_token


def _extract_user_from_request(request: Request) -> Optional[dict]:
    """Gracefully extract basic user details for template headers during exception handling."""
    try:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        if token:
            payload = verify_session_token(token)
            if payload:
                return {"username": payload.get("sub"), "role": payload.get("role")}
    except Exception:
        pass
    return None


def register_exception_handlers(app: FastAPI, templates) -> None:
    """Register custom HTTP and unhandled server exception handlers on FastAPI instance."""

    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        accept = request.headers.get("accept", "")
        is_api = request.url.path.startswith("/api/")
        if exc.status_code == 404 and "text/html" in accept and not is_api:
            user = _extract_user_from_request(request)
            return templates.TemplateResponse(
                request=request,
                name="404.html",
                context={"active_page": None, "current_user": user},
                status_code=404,
            )
        if exc.status_code == 500 and "text/html" in accept and not is_api:
            user = _extract_user_from_request(request)
            return templates.TemplateResponse(
                request=request,
                name="500.html",
                context={"active_page": None, "current_user": user},
                status_code=500,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def custom_500_exception_handler(request: Request, exc: Exception):
        logging.getLogger("ims").exception("Unhandled server exception: %s", exc)
        accept = request.headers.get("accept", "")
        is_api = request.url.path.startswith("/api/")
        if "text/html" in accept and not is_api:
            user = _extract_user_from_request(request)
            return templates.TemplateResponse(
                request=request,
                name="500.html",
                context={"active_page": None, "current_user": user},
                status_code=500,
            )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
