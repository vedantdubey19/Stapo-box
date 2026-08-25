"""Unit tests for deterministic platform surface mapping per Docs/03_RULE_SETS.md §2."""

from backend.agent.surface_mapping import get_platform_surface


def test_surface_mapping_mcq():
    assert get_platform_surface("MCQ", "Easy") == "Story"
    assert get_platform_surface("MCQ", "Hard") == "Story"


def test_surface_mapping_true_false():
    assert get_platform_surface("True/False", "Easy") == "Story"
    assert get_platform_surface("True/False", "Medium") == "Story"


def test_surface_mapping_this_or_that():
    assert get_platform_surface("This-or-That", "Easy") == "Story"
    assert get_platform_surface("This-or-That", "Hard") == "Story"


def test_surface_mapping_fill_blank():
    assert get_platform_surface("Fill in the Blank", "Easy") == "Feed"
    assert get_platform_surface("Fill in the Blank", "Hard") == "Feed"


def test_surface_mapping_guess_number():
    assert get_platform_surface("Guess the Number", "Easy") == "Feed"
    assert get_platform_surface("Guess the Number", "Medium") == "Feed"
    assert get_platform_surface("Guess the Number", "Hard") == "Reel Caption"
