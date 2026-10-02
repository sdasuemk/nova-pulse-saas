import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.database import init_db, engine, AsyncSessionLocal
from app.core.exceptions import register_exception_handlers
from app.api.v1.api_router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] mode...")
    await init_db()
    logger.info("Application startup complete.")
    yield
    # Shutdown
    logger.info("Shutting down application, disposing database connections...")
    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Production-Grade Multi-Tenant SaaS Engine built with FastAPI, Async SQLAlchemy 2.0, RBAC, and WebSockets.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Performance & Request Tracing Middleware
@app.middleware("http")
async def add_process_time_and_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    # Pass request_id through request state
    request.state.request_id = request_id

    response = await call_next(request)

    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    response.headers["X-Request-ID"] = request_id
    return response


# 3. Register centralized domain exception handlers
register_exception_handlers(app)


# 4. Health Check Endpoint
@app.get("/health", tags=["Health & Ops"])
async def health_check():
    """Liveness and database readiness probe."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Health check DB probe failed: {e}")
        db_status = "unhealthy"

    return {
        "status": "online" if db_status == "healthy" else "degraded",
        "project": settings.PROJECT_NAME,
        "database": db_status,
        "environment": settings.ENVIRONMENT,
    }


# 5. Include API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API. Explore docs at /docs",
        "docs_url": "/docs",
        "health_url": "/health",
    }
