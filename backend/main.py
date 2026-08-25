"""FastAPI application entry point.

Exposes REST endpoints for sports engagement content generation.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.agent.schemas import GenerateItemRequest, GenerateItemResponse, MCQSchema
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

# Enable CORS for Streamlit / external clients
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
