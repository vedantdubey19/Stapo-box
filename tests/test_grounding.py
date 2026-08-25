"""Unit tests for Grounding Verification Engine per Docs/03_RULE_SETS.md §5."""

import pytest
from backend.agent.grounding import (
    extract_numbers_from_text,
    verify_text_grounding,
    verify_numeric_grounding,
    verify_grounding,
)


def test_positive_text_grounding_exact():
    """Test exact text match in context returns is_grounded=True with 100% score."""
    context = "Brian Lara scored 400 not out against England at Antigua in 2004."
    claim = "Brian Lara"
    is_grounded, score, msg = verify_text_grounding(claim, context)
    assert is_grounded is True
    assert score == 100.0
    assert "Exact substring match" in msg


def test_negative_text_grounding_hallucinated():
    """Test hallucinated / mismatched answer is correctly flagged as ungrounded."""
    context = "Sachin Tendulkar is the all-time leading run-scorer in international cricket with 100 centuries."
    hallucinated_claim = "Ricky Ponting"
    is_grounded, score, msg = verify_text_grounding(hallucinated_claim, context)
    assert is_grounded is False
    assert score < 85.0
    assert "not verified in context" in msg


def test_fuzzy_text_grounding():
    """Test fuzzy matching handles minor whitespace, casing, and partial names."""
    context = "Muttiah Muralitharan took 800 wickets in Test cricket history."
    claim = "muttiah muralidaran"  # slight phonetic misspelling
    is_grounded, score, msg = verify_text_grounding(claim, context, threshold=80.0)
    assert is_grounded is True
    assert score >= 80.0


def test_numeric_grounding_exact():
    """Test numeric grounding matches exact target number in context."""
    context = "Rohit Sharma scored 264 runs off 173 balls against Sri Lanka."
    is_grounded, score, msg = verify_numeric_grounding(264.0, context)
    assert is_grounded is True
    assert score == 100.0


def test_numeric_grounding_negative():
    """Test numeric grounding fails when target number is absent from context."""
    context = "Michael Jordan scored 63 points against the Boston Celtics in 1986."
    is_grounded, score, msg = verify_numeric_grounding(100.0, context)
    assert is_grounded is False
    assert score == 0.0
    assert "not found" in msg


def test_extract_numbers_from_text():
    """Test number extraction handles integers, decimals, and comma-formatted numbers."""
    text = "The 1950 World Cup match at Maracana had 199,854 spectators, with 4.5 average goals per game."
    nums = extract_numbers_from_text(text)
    assert 1950.0 in nums
    assert 199854.0 in nums
    assert 4.5 in nums


def test_this_or_that_grounding_exempt():
    """Test This-or-That is structurally exempt from grounding check."""
    is_grounded, score, msg = verify_grounding(
        claimed_fact="Option A",
        retrieved_context=None,
        content_type="This-or-That",
    )
    assert is_grounded is True
    assert "opinion-based" in msg


def test_grounding_missing_context_fails():
    """Test factual types fail grounding when context is missing."""
    is_grounded, score, msg = verify_grounding(
        claimed_fact="Lionel Messi",
        retrieved_context=None,
        content_type="MCQ",
    )
    assert is_grounded is False
    assert "Missing retrieved context" in msg
