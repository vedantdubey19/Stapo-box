"""Unit tests for semantic deduplication and persistent history in ChromaDB per Docs/03_RULE_SETS.md §6."""

import shutil
import tempfile
from pathlib import Path
import pytest
from backend.retrieval.vector_store import VectorStore


@pytest.fixture
def temp_vector_store():
    """Create a temporary isolated VectorStore instance for testing."""
    temp_dir = tempfile.mkdtemp()
    store = VectorStore(persist_dir=temp_dir)
    yield store
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_dedup_detects_identical_and_similar_items(temp_vector_store):
    """Test that identical or highly similar questions are flagged as duplicates."""
    sport = "Cricket"
    c_type = "MCQ"
    original_text = "Who holds the record for the highest individual score in Test cricket?"
    similar_text = "Who has the record for the highest individual score in Test cricket history?"
    different_text = "Which country won the inaugural ICC Men's T20 World Cup in 2007?"

    # Initially empty history
    is_dup, score, _ = temp_vector_store.is_duplicate(sport, c_type, original_text)
    assert is_dup is False

    # Record first item
    temp_vector_store.record_generated_item(sport, c_type, original_text, "item_1")

    # Identical query
    is_dup_exact, score_exact, match_exact = temp_vector_store.is_duplicate(sport, c_type, original_text)
    assert is_dup_exact is True
    assert score_exact >= 0.95
    assert match_exact == original_text

    # Highly similar query
    is_dup_sim, score_sim, _ = temp_vector_store.is_duplicate(sport, c_type, similar_text, threshold=0.85)
    assert is_dup_sim is True

    # Materially different query
    is_dup_diff, score_diff, _ = temp_vector_store.is_duplicate(sport, c_type, different_text)
    assert is_dup_diff is False


def test_dedup_history_persists_across_instances():
    """Test that generation history persists across VectorStore re-initializations."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Instance 1: write item
        store1 = VectorStore(persist_dir=temp_dir)
        store1.record_generated_item("Football", "True/False", "Brazil has won 5 World Cups.", "item_fb_1")
        assert store1.history_collection.count() == 1

        # Instance 2: re-open from same disk directory
        store2 = VectorStore(persist_dir=temp_dir)
        assert store2.history_collection.count() == 1
        is_dup, score, _ = store2.is_duplicate("Football", "True/False", "Brazil has won 5 World Cups.")
        assert is_dup is True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
