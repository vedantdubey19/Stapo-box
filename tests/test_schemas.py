"""Unit tests for Pydantic content schemas per Docs/03_RULE_SETS.md §1."""

import pytest
from pydantic import ValidationError
from backend.agent.schemas import MCQSchema


def test_mcq_schema_valid():
    """Test valid MCQ item instantiates without errors."""
    valid_data = {
        "sport": "Cricket",
        "difficulty": "Medium",
        "question": "Who holds the record for the highest individual score in Test cricket?",
        "options": {
            "A": "Brian Lara",
            "B": "Sachin Tendulkar",
            "C": "Don Bradman",
            "D": "Matthew Hayden",
        },
        "correct_answer": "A",
        "explanation": "Brian Lara scored 400 not out against England in 2004 at St. John's, Antigua.",
        "source": "vector_db",
        "platform_surface": "Story",
        "grounded": True,
    }
    item = MCQSchema.model_validate(valid_data)
    assert item.sport == "Cricket"
    assert item.correct_answer == "A"
    assert len(item.options) == 4
    assert item.options["A"] == "Brian Lara"


def test_mcq_schema_invalid_keys():
    """Test MCQ fails if options are not exactly A, B, C, D."""
    invalid_data = {
        "sport": "Football",
        "difficulty": "Easy",
        "question": "Which country won the 2018 FIFA World Cup?",
        "options": {
            "1": "France",
            "2": "Croatia",
            "3": "Brazil",
            "4": "Germany",
        },
        "correct_answer": "1",
        "explanation": "France won 4-2 in the final.",
        "source": "vector_db",
        "platform_surface": "Story",
        "grounded": True,
    }
    with pytest.raises(ValidationError):
        MCQSchema.model_validate(invalid_data)


def test_mcq_schema_missing_option():
    """Test MCQ fails if options has fewer than 4 items."""
    invalid_data = {
        "sport": "Football",
        "difficulty": "Easy",
        "question": "Which country won the 2018 FIFA World Cup?",
        "options": {
            "A": "France",
            "B": "Croatia",
            "C": "Brazil",
        },
        "correct_answer": "A",
        "explanation": "France won 4-2.",
        "source": "vector_db",
        "platform_surface": "Story",
        "grounded": True,
    }
    with pytest.raises(ValidationError):
        MCQSchema.model_validate(invalid_data)


def test_mcq_schema_correct_answer_not_in_options():
    """Test MCQ fails if correct_answer key is not present in options."""
    invalid_data = {
        "sport": "Tennis",
        "difficulty": "Hard",
        "question": "Who won the 2008 Wimbledon men's singles final?",
        "options": {
            "A": "Rafael Nadal",
            "B": "Roger Federer",
            "C": "Novak Djokovic",
            "D": "Andy Murray",
        },
        "correct_answer": "E",  # Invalid key
        "explanation": "Rafael Nadal defeated Roger Federer in 5 sets.",
        "source": "vector_db",
        "platform_surface": "Story",
        "grounded": True,
    }
    with pytest.raises(ValidationError):
        MCQSchema.model_validate(invalid_data)


def test_mcq_schema_empty_option_string():
    """Test MCQ fails if an option text is empty or whitespace."""
    invalid_data = {
        "sport": "Basketball",
        "difficulty": "Easy",
        "question": "How many points is a shot made from beyond the arc worth?",
        "options": {
            "A": "3",
            "B": " ",
            "C": "2",
            "D": "1",
        },
        "correct_answer": "A",
        "explanation": "A shot from beyond the arc is worth 3 points.",
        "source": "vector_db",
        "platform_surface": "Story",
        "grounded": True,
    }
    with pytest.raises(ValidationError):
        MCQSchema.model_validate(invalid_data)
