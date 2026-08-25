"""FastAPI application entry point.

Exposes REST endpoints for single item generation, batch generation,
per-item regeneration, full batch regeneration, and telemetry analytics.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.agent.schemas import (
    GenerateItemRequest,
    GenerateItemResponse,
    GenerateBatchRequest,
    GenerateBatchResponse,
    RegenerateItemRequest,
    RegenerateItemResponse,
)
from backend.agent.orchestrator import orchestrator

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info("🚀 StapuBox Sports Agent Backend starting up...")
    logger.info(f"   Provider: {settings.LLM_PROVIDER} | Model: {settings.GEMINI_MODEL}")
    yield
    logger.info("🛑 StapuBox Sports Agent Backend shutting down...")


app = FastAPI(
    title="StapuBox Sports Engagement Content Agent API",
    version="1.0.0",
    description="AI Agent generating grounded, Instagram-ready sports trivia, polls, and challenges.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "healthy",
        "provider": settings.LLM_PROVIDER,
        "allowed_sports": settings.ALLOWED_SPORTS,
        "allowed_difficulties": settings.ALLOWED_DIFFICULTIES,
        "allowed_content_types": settings.ALLOWED_CONTENT_TYPES,
    }


@app.get("/analytics", tags=["Telemetry"])
def get_analytics():
    """Return runtime telemetry statistics (grounding rate, source distribution, dedup counts)."""
    return orchestrator.telemetry.get_stats()


@app.post("/generate/item", response_model=GenerateItemResponse, tags=["Generation"])
def generate_single_item(payload: GenerateItemRequest):
    """Generate a single validated sports engagement item."""
    if payload.sport not in settings.ALLOWED_SPORTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sport '{payload.sport}'. Must be one of {settings.ALLOWED_SPORTS}",
        )
    if payload.difficulty not in settings.ALLOWED_DIFFICULTIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid difficulty '{payload.difficulty}'. Must be one of {settings.ALLOWED_DIFFICULTIES}",
        )

    try:
        item = orchestrator.generate_single_item(
            sport=payload.sport,
            difficulty=payload.difficulty,
            content_type=payload.content_type,
            topic_hint=payload.topic_hint,
        )
        return GenerateItemResponse(
            success=True,
            content_type=payload.content_type,
            item=item,
        )
    except Exception as e:
        logger.error(f"Failed to generate item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation failed: {str(e)}",
        )


@app.post("/generate/batch", response_model=GenerateBatchResponse, tags=["Generation"])
def generate_batch(payload: GenerateBatchRequest):
    """Generate a batch of 4-5 items with mixed or uniform content types."""
    if payload.sport not in settings.ALLOWED_SPORTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sport '{payload.sport}'. Must be one of {settings.ALLOWED_SPORTS}",
        )
    if payload.difficulty not in settings.ALLOWED_DIFFICULTIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid difficulty '{payload.difficulty}'. Must be one of {settings.ALLOWED_DIFFICULTIES}",
        )

    try:
        items = orchestrator.generate_batch(
            sport=payload.sport,
            difficulty=payload.difficulty,
            count=payload.count,
            content_types=payload.content_types,
            topic_hint=payload.topic_hint,
        )
        return GenerateBatchResponse(
            success=True,
            sport=payload.sport,
            difficulty=payload.difficulty,
            total_items=len(items),
            items=items,
        )
    except Exception as e:
        logger.error(f"Failed to generate batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch generation failed: {str(e)}",
        )


@app.post("/regenerate/item", response_model=RegenerateItemResponse, tags=["Generation"])
def regenerate_item(payload: RegenerateItemRequest):
    """Regenerate a single item in place."""
    try:
        item = orchestrator.regenerate_single_item(
            sport=payload.sport,
            difficulty=payload.difficulty,
            content_type=payload.content_type,
            topic_hint=payload.topic_hint,
        )
        return RegenerateItemResponse(
            success=True,
            item=item,
        )
    except Exception as e:
        logger.error(f"Failed to regenerate item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regeneration failed: {str(e)}",
        )


@app.post("/regenerate/batch", response_model=GenerateBatchResponse, tags=["Generation"])
def regenerate_batch(payload: GenerateBatchRequest):
    """Regenerate an entire batch of items."""
    return generate_batch(payload)
