"""
Main FastAPI application entry point for Aanya Assistant.
"""
import os
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.config import get_settings
from backend.core.database import check_db_connection
from backend.core.scheduler import start_scheduler, shutdown_scheduler, get_scheduler_status
from backend.core.coordinator import coordinator, AssistantRequest, RoutingDecision
from backend.schemas import StandardResponse, HealthResponse
from backend.modules.jobs import router as jobs_router
from backend.modules.finance import router as finance_router
from backend.modules.ocr import router as ocr_router
from backend.modules.math_logic import router as math_logic_router
from backend.modules.reminders import router as reminders_router
from backend.modules.health import router as health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aanya.app")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    Handles startup and shutdown sequence safely.
    """
    logger.info("Initializing Aanya Assistant (environment: %s)...", settings.ENVIRONMENT)
    try:
        start_scheduler()
    except Exception as exc:
        logger.error("Failed to start scheduler during startup: %s", exc)

    yield

    logger.info("Shutting down Aanya Assistant...")
    try:
        shutdown_scheduler(wait=False)
    except Exception as exc:
        logger.error("Error stopping scheduler: %s", exc)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Aanya - Self-Hosted Personal AI Assistant Foundation",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# CORS Middleware with strict/configured origin whitelist
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Centralized Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Normalize HTTPExceptions into standard JSON structure."""
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardResponse(
            success=False,
            error=str(exc.detail),
            data=None,
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Normalize Pydantic request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=StandardResponse(
            success=False,
            error="Validation Error",
            data={"details": jsonable_encoder(exc.errors())},
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all unhandled exception handler."""
    logger.exception("Unhandled server exception at %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=StandardResponse(
            success=False,
            error="An internal server error occurred.",
            data=None,
        ).model_dump(mode="json"),
    )


# Health Check Endpoint
@app.get("/api/health", response_model=StandardResponse[HealthResponse])
def health_check():
    """
    Health check endpoint.
    Verifies actual database connectivity and scheduler status.
    Returns status 'ok' when all systems are operational, or 'degraded' if a component is unreachable.
    """
    db_ok, db_detail = check_db_connection()
    scheduler_diag = get_scheduler_status()

    is_overall_ok = db_ok
    status_label = "ok" if is_overall_ok else "degraded"

    payload = HealthResponse(
        status=status_label,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database="connected" if db_ok else db_detail,
        scheduler=scheduler_diag,
        timestamp=datetime.now(timezone.utc),
    )

    return StandardResponse(
        success=is_overall_ok,
        data=payload,
        error=None if is_overall_ok else f"Degraded service health: database {db_detail}",
    )


# Coordinator Router Endpoint
@app.post("/api/coordinator/route", response_model=StandardResponse[RoutingDecision])
def route_assistant_request(request: AssistantRequest):
    """
    Coordinator routing endpoint.
    Classifies incoming requests and routes them toward the responsible capability module.
    """
    decision = coordinator.route(request)
    return StandardResponse(
        success=True,
        data=decision,
    )


# Register Feature Module Routers under /api
app.include_router(jobs_router, prefix="/api")
app.include_router(finance_router, prefix="/api")
app.include_router(ocr_router, prefix="/api")
app.include_router(math_logic_router, prefix="/api")
app.include_router(reminders_router, prefix="/api")
app.include_router(health_router, prefix="/api")

# Static frontend assets and PWA shell mounting (for local development without Caddy)
_frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(_frontend_dir):
    _static_dir = os.path.join(_frontend_dir, "static")
    if os.path.isdir(_static_dir):
        app.mount("/static", StaticFiles(directory=_static_dir), name="static")

    @app.get("/manifest.json", include_in_schema=False)
    def get_manifest():
        return FileResponse(os.path.join(_frontend_dir, "manifest.json"), media_type="application/manifest+json")

    @app.get("/service-worker.js", include_in_schema=False)
    def get_service_worker():
        return FileResponse(os.path.join(_frontend_dir, "service-worker.js"), media_type="application/javascript")

    @app.get("/index.html", include_in_schema=False)
    def get_index_html():
        return FileResponse(os.path.join(_frontend_dir, "index.html"), media_type="text/html")

    @app.get("/", include_in_schema=False)
    def get_root():
        return FileResponse(os.path.join(_frontend_dir, "index.html"), media_type="text/html")
