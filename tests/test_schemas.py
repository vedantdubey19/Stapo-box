"""Unit tests for Pydantic content schemas across all 5 types per Docs/03_RULE_SETS.md §1."""

import pytest
from pydantic import ValidationError
from backend.agent.schemas import (
    MCQSchema,
    TrueFalseSchema,
    ThisOrThatSchema,
    FillBlankSchema,
    GuessNumberSchema,
)


# ── MCQ Tests ───────────────────────────────────────────────────────────────────

def test_mcq_schema_valid():
    """Test valid MCQ item instantiates without errors."""
    data = {
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
        "explanation": "Brian Lara scored 400 not out against England in 2004.",
        "source": "vector_db",
        "platform_surface": "Story",
        "grounded": True,
    }
    item = MCQSchema.model_validate(data)
    assert item.correct_answer == "A"
    assert len(item.options) == 4


def test_mcq_schema_invalid_keys():
    """Test MCQ fails if options are not A, B, C, D."""
    data = {
        "sport": "Football",
        "difficulty": "Easy",
        "question": "Which country won the 2018 World Cup?",
        "options": {"1": "France", "2": "Croatia", "3": "Brazil", "4": "Germany"},
        "correct_answer": "1",
        "explanation": "France won 4-2.",
        "source": "vector_db",
        "platform_surface": "Story",
        "grounded": True,
    }
    with pytest.raises(ValidationError):
        MCQSchema.model_validate(data)


# ── True / False Tests ──────────────────────────────────────────────────────────

def test_true_false_schema_valid():
    """Test valid True/False schema."""
    data = {
        "sport": "Tennis",
        "difficulty": "Easy",
        "statement": "Wimbledon is the only Grand Slam played on natural grass courts.",
        "correct_answer": True,
        "explanation": "Wimbledon is famously held on grass at the All England Club.",
        "source": "vector_db",
        "platform_surface": "Story",
        "grounded": True,
    }
    item = TrueFalseSchema.model_validate(data)
    assert item.correct_answer is True
    assert item.platform_surface == "Story"


# ── This-or-That Tests ─────────────────────────────────────────────────────────

def test_this_or_that_schema_valid():
    """Test valid This-or-That debate schema."""
    data = {
        "sport": "Football",
        "prompt": "Prime Messi (2012) vs Prime CR7 (2012): Who was more lethal?",
        "options": ["Prime Messi", "Prime Cristiano Ronaldo"],
        "is_opinion": True,
        "platform_surface": "Story",
    }
    item = ThisOrThatSchema.model_validate(data)
    assert len(item.options) == 2
    assert item.is_opinion is True
    assert not hasattr(item, "correct_answer")


def test_this_or_that_invalid_options_count():
    """Test This-or-That fails if options length is not 2."""
    data = {
        "sport": "Basketball",
        "prompt": "Pick your GOAT:",
        "options": ["Michael Jordan", "LeBron James", "Kobe Bryant"],  # 3 options -> invalid!
        "is_opinion": True,
        "platform_surface": "Story",
    }
    with pytest.raises(ValidationError):
        ThisOrThatSchema.model_validate(data)


# ── Fill in the Blank Tests ───────────────────────────────────────────────────

def test_fill_blank_schema_valid():
    """Test valid Fill in the Blank schema."""
    data = {
        "sport": "Badminton",
        "difficulty": "Easy",
        "sentence": "A standard competitive feather shuttlecock is made with exactly ___ goose feathers.",
        "options": ["12", "14", "16", "18"],
        "correct_answer": "16",
        "explanation": "Official BWF regulations mandate 16 feathers.",
        "source": "vector_db",
        "platform_surface": "Feed",
        "grounded": True,
    }
    item = FillBlankSchema.model_validate(data)
    assert item.sentence.count("___") == 1
    assert item.correct_answer in item.options


def test_fill_blank_missing_marker():
    """Test Fill in the Blank fails if '___' is missing."""
    data = {
        "sport": "Badminton",
        "difficulty": "Easy",
        "sentence": "A standard feather shuttlecock has 16 goose feathers.",
        "options": ["12", "14", "16", "18"],
        "correct_answer": "16",
        "explanation": "Regulations mandate 16 feathers.",
        "source": "vector_db",
        "platform_surface": "Feed",
        "grounded": True,
    }
    with pytest.raises(ValidationError):
        FillBlankSchema.model_validate(data)


# ── Guess the Number Tests ────────────────────────────────────────────────────

def test_guess_number_schema_valid():
    """Test valid Guess the Number schema."""
    data = {
        "sport": "Basketball",
        "difficulty": "Hard",
        "question": "How many total points did Wilt Chamberlain score in his iconic 1962 single-game record?",
        "target_number": 100.0,
        "tolerance": 0.0,
        "explanation": "Wilt Chamberlain scored 100 points for the Warriors against the Knicks.",
        "source": "vector_db",
        "platform_surface": "Reel Caption",
        "grounded": True,
    }
    item = GuessNumberSchema.model_validate(data)
    assert item.target_number == 100.0
    assert item.tolerance == 0.0


def test_guess_number_negative_tolerance():
    """Test Guess the Number fails if tolerance is negative."""
    data = {
        "sport": "Basketball",
        "difficulty": "Hard",
        "question": "How many points did Wilt score?",
        "target_number": 100.0,
        "tolerance": -5.0,  # Negative tolerance -> invalid!
        "explanation": "100 points.",
        "source": "vector_db",
        "platform_surface": "Reel Caption",
        "grounded": True,
    }
    with pytest.raises(ValidationError):
        GuessNumberSchema.model_validate(data)
