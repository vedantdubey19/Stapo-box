"""End-to-end tests for Orchestrator and FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.agent.orchestrator import orchestrator
from backend.agent.schemas import MCQSchema, TrueFalseSchema, ThisOrThatSchema, FillBlankSchema, GuessNumberSchema

client = TestClient(app)


def test_health_check_endpoint():
    """Verify healthcheck endpoint returns healthy status with supported sports and types."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "Cricket" in data["allowed_sports"]
    assert "MCQ" in data["allowed_content_types"]


def test_generate_single_item_endpoint_invalid_sport():
    """Verify endpoint rejects invalid sports with HTTP 400."""
    resp = client.post(
        "/generate/item",
        json={"sport": "Curling", "difficulty": "Medium", "content_type": "MCQ"},
    )
    assert resp.status_code == 400
    assert "Invalid sport" in resp.json()["detail"]


def test_generate_single_item_endpoint_invalid_difficulty():
    """Verify endpoint rejects invalid difficulty with HTTP 422 validation error."""
    resp = client.post(
        "/generate/item",
        json={"sport": "Cricket", "difficulty": "Extreme", "content_type": "MCQ"},
    )
    assert resp.status_code == 422


def test_analytics_endpoint():
    """Verify telemetry analytics endpoint returns valid structure."""
    resp = client.get("/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_items_generated" in data
    assert "grounding_success_rate_pct" in data
    assert "sources" in data
    assert "surfaces" in data


def test_orchestrator_routing_rules():
    """Verify retrieval routing rules according to Docs/03_RULE_SETS.md §3."""
    # This-or-That should never retrieve
    ctx, source = orchestrator.route_and_retrieve("Tennis", "Easy", "This-or-That")
    assert ctx is None
    assert source == "none"

    # Factual types for existing seed sport should use vector_db
    ctx, source = orchestrator.route_and_retrieve("Cricket", "Medium", "MCQ")
    assert ctx is not None
    assert source == "vector_db"

    # Recency hint should prioritize web_search
    ctx, source = orchestrator.route_and_retrieve("Football", "Easy", "MCQ", topic_hint="2024 recent season")
    assert ctx is not None
    assert source in ["web_search", "vector_db"]


def test_orchestrator_fact_extraction():
    """Verify fact extraction helper correctly targets verifying fields per type."""
    mcq = MCQSchema(
        sport="Cricket",
        difficulty="Easy",
        question="Who scored 100 centuries?",
        options={"A": "Sachin Tendulkar", "B": "A", "C": "B", "D": "C"},
        correct_answer="A",
        explanation="Sachin scored 100 centuries.",
        source="vector_db",
        platform_surface="Story",
        grounded=True,
    )
    assert orchestrator._extract_fact_to_verify(mcq, "MCQ") == "Sachin Tendulkar"

    tf = TrueFalseSchema(
        sport="Tennis",
        difficulty="Easy",
        statement="Wimbledon is played on grass.",
        correct_answer=True,
        explanation="Wimbledon is grass.",
        source="vector_db",
        platform_surface="Story",
        grounded=True,
    )
    assert orchestrator._extract_fact_to_verify(tf, "True/False") == "Wimbledon is played on grass."

    fb = FillBlankSchema(
        sport="Basketball",
        difficulty="Easy",
        sentence="A free throw is worth ___ point.",
        options=["1", "2", "3", "4"],
        correct_answer="1",
        explanation="Free throw is 1 point.",
        source="vector_db",
        platform_surface="Feed",
        grounded=True,
    )
    assert orchestrator._extract_fact_to_verify(fb, "Fill in the Blank") == "1"

    gn = GuessNumberSchema(
        sport="Cricket",
        difficulty="Medium",
        question="How many runs did Rohit Sharma score in his ODI world record?",
        target_number=264.0,
        tolerance=0.0,
        explanation="Rohit scored 264 runs.",
        source="vector_db",
        platform_surface="Feed",
        grounded=True,
    )
    assert orchestrator._extract_fact_to_verify(gn, "Guess the Number") == 264.0
