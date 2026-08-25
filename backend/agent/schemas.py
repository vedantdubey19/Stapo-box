"""Pydantic data schemas for content types and API requests/responses.

Enforces strict structural rules per Docs/03_RULE_SETS.md §1:
- MCQ: Exactly 4 options labeled A/B/C/D, correct_answer must be in options.
- True/False: statement + boolean correct_answer.
- This-or-That: 2 options, is_opinion=True, NO correct_answer or grounded field.
- Fill in the Blank: sentence with single '___' blank marker, 4 options.
- Guess the Number: question, target_number, tolerance >= 0.
- Batch generation and regeneration payloads.
"""

from typing import Annotated, Dict, List, Literal, Optional, Union
import uuid
from pydantic import BaseModel, Field, field_validator, model_validator


# ── 1. MCQ Schema ────────────────────────────────────────────────────────────────

class MCQSchema(BaseModel):
    """Multiple Choice Question schema with labeled A/B/C/D options."""
    sport: str = Field(..., description="Sport category")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(..., description="Difficulty tier")
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


# ── 2. True / False Schema ───────────────────────────────────────────────────────

class TrueFalseSchema(BaseModel):
    """True or False statement schema."""
    sport: str = Field(..., description="Sport category")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(..., description="Difficulty tier")
    statement: str = Field(..., min_length=5, description="Factual or false sports statement")
    correct_answer: bool = Field(..., description="True if statement is factually correct, False otherwise")
    explanation: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Concise explanation justifying True or False (<= 300 chars)",
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
        description="Whether the statement was verified against context",
    )


# ── 3. This-or-That Schema (Opinion Poll) ────────────────────────────────────────

class ThisOrThatSchema(BaseModel):
    """This-or-That debate poll schema. Opinion-based, no correct answer or grounding."""
    sport: str = Field(..., description="Sport category")
    prompt: str = Field(..., min_length=5, description="Debatable poll question or topic")
    options: List[str] = Field(..., description="Exactly 2 debate choices")
    is_opinion: Literal[True] = Field(
        default=True,
        description="Must always be True (opinion poll)",
    )
    platform_surface: Literal["Story", "Feed", "Reel Caption"] = Field(
        default="Story",
        description="Optimal Instagram placement surface (Story Poll sticker)",
    )

    @field_validator("options")
    @classmethod
    def validate_exactly_two_options(cls, v: List[str]) -> List[str]:
        if len(v) != 2:
            raise ValueError(f"This-or-That options must have exactly 2 items, got {len(v)}")
        for opt in v:
            if not isinstance(opt, str) or not opt.strip():
                raise ValueError("Options must be non-empty strings")
        return v


# ── 4. Fill in the Blank Schema ──────────────────────────────────────────────────

class FillBlankSchema(BaseModel):
    """Fill in the Blank schema with single blank marker and 4 choices."""
    sport: str = Field(..., description="Sport category")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(..., description="Difficulty tier")
    sentence: str = Field(
        ...,
        min_length=5,
        description="Sentence containing exactly one '___' blank marker",
    )
    options: List[str] = Field(..., description="Exactly 4 completion options")
    correct_answer: str = Field(..., description="The word/phrase filling the blank (must be in options)")
    explanation: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Concise explanation confirming the answer (<= 300 chars)",
    )
    source: Literal["web_search", "vector_db", "both"] = Field(
        default="vector_db",
        description="Origin of retrieved facts",
    )
    platform_surface: Literal["Story", "Feed", "Reel Caption"] = Field(
        default="Feed",
        description="Optimal Instagram placement surface",
    )
    grounded: bool = Field(
        default=True,
        description="Whether the fact was verified in retrieved context",
    )

    @field_validator("sentence")
    @classmethod
    def validate_single_blank_marker(cls, v: str) -> str:
        count = v.count("___")
        if count != 1:
            raise ValueError(f"Sentence must contain exactly one '___' blank marker, found {count}")
        return v

    @field_validator("options")
    @classmethod
    def validate_four_options(cls, v: List[str]) -> List[str]:
        if len(v) != 4:
            raise ValueError(f"Fill in the Blank options must contain exactly 4 items, got {len(v)}")
        for opt in v:
            if not isinstance(opt, str) or not opt.strip():
                raise ValueError("Options must be non-empty strings")
        return v

    @model_validator(mode="after")
    def validate_correct_answer_in_options(self) -> "FillBlankSchema":
        if self.correct_answer not in self.options:
            raise ValueError(f"correct_answer '{self.correct_answer}' must be present in options list {self.options}")
        return self


# ── 5. Guess the Number Schema ───────────────────────────────────────────────────

class GuessNumberSchema(BaseModel):
    """Guess the Number numeric engagement schema."""
    sport: str = Field(..., description="Sport category")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(..., description="Difficulty tier")
    question: str = Field(..., min_length=5, description="Numerical sports question")
    target_number: float = Field(..., description="Exact numerical answer")
    tolerance: float = Field(..., ge=0.0, description="Acceptable numerical tolerance margin (>= 0)")
    explanation: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Explanation revealing the exact number and context (<= 300 chars)",
    )
    source: Literal["web_search", "vector_db", "both"] = Field(
        default="vector_db",
        description="Origin of retrieved facts",
    )
    platform_surface: Literal["Story", "Feed", "Reel Caption"] = Field(
        default="Feed",
        description="Optimal Instagram placement surface",
    )
    grounded: bool = Field(
        default=True,
        description="Whether the number was verified in retrieved context",
    )


class ItemErrorSchema(BaseModel):
    """Fallback error schema for items that failed generation gracefully."""
    error: str = Field(default="generation_failed", description="Error type identifier")
    message: str = Field(..., description="Human-readable error description")
    sport: str = Field(..., description="Target sport")
    difficulty: str = Field(default="Medium", description="Target difficulty")
    content_type: str = Field(..., description="Target content type")
    platform_surface: str = Field(default="Story", description="Target surface")


# ── Unified Item Types ───────────────────────────────────────────────────────────

ContentItemPayload = Union[
    MCQSchema,
    TrueFalseSchema,
    ThisOrThatSchema,
    FillBlankSchema,
    GuessNumberSchema,
    ItemErrorSchema,
]


class BatchItemWrapper(BaseModel):
    """Container wrapping an individual item within a batch with an identifier."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    content_type: str
    item: ContentItemPayload


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
    topic_hint: Optional[str] = Field(default=None, description="Optional focus area or recency hint")


class GenerateItemResponse(BaseModel):
    """Response payload returning a generated item."""
    success: bool = True
    content_type: str
    item: ContentItemPayload
    error: Optional[str] = None


class GenerateBatchRequest(BaseModel):
    """Request payload to generate a batch of 4-5 engagement content items."""
    sport: str = Field(default="Cricket", description="Sport category")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(default="Medium", description="Difficulty level")
    count: int = Field(default=5, ge=4, le=5, description="Number of items to generate (4 or 5)")
    content_types: List[str] = Field(
        default_factory=lambda: [
            "MCQ",
            "True/False",
            "This-or-That",
            "Fill in the Blank",
            "Guess the Number",
        ],
        description="Types of content to include in batch",
    )
    topic_hint: Optional[str] = Field(default=None, description="Optional topic hint")


class GenerateBatchResponse(BaseModel):
    """Response payload returning a batch of items."""
    success: bool = True
    sport: str
    difficulty: str
    total_items: int
    items: List[BatchItemWrapper]
    error: Optional[str] = None


class RegenerateItemRequest(BaseModel):
    """Request payload to regenerate a specific item in a batch."""
    sport: str = Field(..., description="Sport category")
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(default="Medium", description="Difficulty level")
    content_type: str = Field(..., description="Content type to regenerate")
    topic_hint: Optional[str] = Field(default=None, description="Optional topic hint")


class RegenerateItemResponse(BaseModel):
    """Response payload returning regenerated single item."""
    success: bool = True
    item: BatchItemWrapper
    error: Optional[str] = None
