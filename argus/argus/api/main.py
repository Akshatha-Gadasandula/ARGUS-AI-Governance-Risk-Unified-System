"""
FastAPI main application for ARGUS.
Sets up the API with database, monitoring, logging, and routers.
"""
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from argus.db.database import create_db_and_tables
from argus.config import settings
from argus.api.routers import registry, monitoring, audit, qa


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Set up standard logging
logging.basicConfig(
    format="%(message)s",
    level=settings.log_level,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("ARGUS Starting up...")
    try:
        await create_db_and_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Non-fatal - continue startup

    yield

    # Shutdown
    logger.info("ARGUS Shutting down...")


# Create FastAPI application
app = FastAPI(
    title="ARGUS - AI Governance & Risk Unified System",
    description="Enterprise platform for governing AI systems across regulatory frameworks",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus monitoring
Instrumentator().instrument(app).expose(app)

app.include_router(registry.router, prefix="/api/v1/registry", tags=["Registry"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["Monitoring"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(qa.router, prefix="/api/v1/qa", tags=["Q&A"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ARGUS",
        "version": "1.0.0",
        "description": "AI Governance & Risk Unified System",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "argus.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
    )
