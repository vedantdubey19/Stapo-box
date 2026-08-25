"""Pydantic data schemas for content types and API requests/responses.

Enforces strict structural rules per Docs/03_RULE_SETS.md §1:
- MCQ: Exactly 4 options labeled A/B/C/D, correct_answer must be in options.
- True/False: statement + boolean correct_answer.
- This-or-That: 2 options, is_opinion=True, NO correct_answer or grounded field.
- Fill in the Blank: sentence with single '___' blank marker, 4 options.
- Guess the Number: question, target_number, tolerance >= 0.
"""

from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# ── Content Item Schemas ─────────────────────────────────────────────────────────

class MCQSchema(BaseModel):
    """Multiple Choice Question schema with labeled A/B/C/D options."""
    sport: str = Field(..., description="Sport category")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(..., description="Difficulty level")
    question: str = Field(..., min_length=5, description="The quiz question")
    options: Dict[Literal["A", "B", "C", "D"], str] = Field(
        ...,
        description="Exactly 4 answer choices keyed as A, B, C, D",
    )
    correct_answer: Literal["A", "B", "C", "D"] = Field(
        ...,
        description="Key of the correct option (A, B, C, or D)",
    )
    explanation: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Concise factual explanation (<= 300 chars)",
    )
    source: Literal["web_search", "vector_db", "both"] = Field(
        default="vector_db",
        description="Origin of retrieved facts",
    )
    platform_surface: Literal["Story", "Feed", "Reel Caption"] = Field(
        default="Story",
        description="Optimal Instagram placement surface",
    )
    grounded: bool = Field(
        default=True,
        description="Whether the fact was verified in retrieved context",
    )

    @field_validator("options")
    @classmethod
    def validate_options_keys_and_values(cls, v: Dict[str, str]) -> Dict[str, str]:
        required_keys = {"A", "B", "C", "D"}
        if set(v.keys()) != required_keys:
            raise ValueError(f"Options must contain exactly keys {required_keys}, got {set(v.keys())}")
        for key, val in v.items():
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"Option '{key}' must be a non-empty string")
        return v

    @model_validator(mode="after")
    def validate_correct_answer_in_options(self) -> "MCQSchema":
        if self.correct_answer not in self.options:
            raise ValueError(f"correct_answer '{self.correct_answer}' must be present in options keys")
        return self


# ── API Request & Response Schemas ───────────────────────────────────────────────

class GenerateItemRequest(BaseModel):
    """Request payload to generate a single engagement content item."""
    sport: str = Field(default="Cricket", description="Sport name")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(default="Medium", description="Difficulty tier")
    content_type: Literal[
        "MCQ",
        "True/False",
        "This-or-That",
        "Fill in the Blank",
        "Guess the Number",
    ] = Field(default="MCQ", description="Type of engagement content")


class GenerateItemResponse(BaseModel):
    """Response payload returning a generated item."""
    success: bool = True
    content_type: str
    item: MCQSchema  # Will become a Union as further content types are added in Phase 4
    error: Optional[str] = None
