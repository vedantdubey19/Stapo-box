"""Fill in the Blank prompt template module per Docs/03_RULE_SETS.md §4."""

from typing import Optional


def build_prompt(
    sport: str,
    difficulty: str,
    retrieved_context: Optional[str] = None,
    error_feedback: Optional[str] = None,
) -> str:
    """Build a specialized prompt for generating a Fill in the Blank sports trivia item."""
    context_section = ""
    if retrieved_context:
        context_section = f"""
--- CONTEXT ---
{retrieved_context}
--- END CONTEXT ---

CRITICAL GROUNDING RULES:
1. Formulate the sentence and missing word/phrase using ONLY the verified facts present in the CONTEXT above.
2. The correct answer MUST be an exact factual term or stat found in the CONTEXT.
"""
    else:
        context_section = """
GROUNDING GUIDELINES:
1. Formulate a 100% verified, indisputable sports trivia statement with a key term missing.
"""

    retry_section = ""
    if error_feedback:
        retry_section = f"""
PREVIOUS ATTEMPT FAILED WITH ERROR:
{error_feedback}
Please fix this issue in your new response.
"""

    return f"""You are an elite sports content creator craft engaging Instagram trivia for sports fans.

TASK:
Create 1 high-engagement "Fill in the Blank" quiz item for Instagram Feed captions.

TARGET SPECIFICATIONS:
- Sport: {sport}
- Difficulty: {difficulty} (Easy: well-known mainstream fact; Medium: enthusiast knowledge; Hard: deep trivia/historical stat)

{context_section}
{retry_section}
FORMAT REQUIREMENTS:
Return a single JSON object with EXACTLY the following keys:
{{
    "sport": "{sport}",
    "difficulty": "{difficulty}",
    "sentence": "<Engaging sentence containing EXACTLY ONE '___' blank marker, e.g. 'Sachin Tendulkar scored his 100th international century against ___ in 2012.'>",
    "options": [
        "<Option 1>",
        "<Option 2>",
        "<Option 3>",
        "<Option 4>"
    ],
    "correct_answer": "<The exact string matching the correct option>",
    "explanation": "<Punchy explanation confirming the missing term, under 300 characters>",
    "source": "vector_db",
    "platform_surface": "Feed",
    "grounded": true
}}

STRICT SCHEMA RULES:
1. The 'sentence' string MUST contain EXACTLY ONE '___' (three underscores) representing the blank.
2. 'options' MUST be a list containing EXACTLY 4 plausible answer choices.
3. 'correct_answer' MUST match one of the 4 items in 'options' word-for-word.
4. Do NOT output markdown code fences outside the JSON.
"""
