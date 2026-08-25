"""Guess the Number prompt template module per Docs/03_RULE_SETS.md §4."""

from typing import Optional


def build_prompt(
    sport: str,
    difficulty: str,
    retrieved_context: Optional[str] = None,
    error_feedback: Optional[str] = None,
) -> str:
    """Build a specialized prompt for generating a Guess the Number sports challenge item."""
    context_section = ""
    if retrieved_context:
        context_section = f"""
--- CONTEXT ---
{retrieved_context}
--- END CONTEXT ---

CRITICAL GROUNDING RULES:
1. The question and target number MUST be extracted DIRECTLY from the verified numerical stats in the CONTEXT above.
2. 'target_number' MUST be an exact numerical stat (float or integer) explicitly stated in the CONTEXT.
3. 'tolerance' should be a sensible margin for fans (e.g. 0 for exact years/records, or 2-5% for large stats).
"""
    else:
        context_section = """
GROUNDING GUIDELINES:
1. Select an iconic, well-documented numerical sports record, year, or statistic.
"""

    retry_section = ""
    if error_feedback:
        retry_section = f"""
PREVIOUS ATTEMPT FAILED WITH ERROR:
{error_feedback}
Please fix this issue in your new response.
"""

    surface_hint = "Reel Caption" if difficulty.capitalize() == "Hard" else "Feed"

    return f"""You are an elite sports content creator craft engaging Instagram trivia for sports fans.

TASK:
Create 1 high-engagement "Guess the Number" interactive challenge for Instagram captions/comments.

TARGET SPECIFICATIONS:
- Sport: {sport}
- Difficulty: {difficulty} (Easy: famous numbers like points in a quarter/titles; Medium: historic single-game stats; Hard: obscure world records)

{context_section}
{retry_section}
FORMAT REQUIREMENTS:
Return a single JSON object with EXACTLY the following keys:
{{
    "sport": "{sport}",
    "difficulty": "{difficulty}",
    "question": "<Engaging numerical challenge question prompting fans to guess in comments>",
    "target_number": 264.0,
    "tolerance": 5.0,
    "explanation": "<Punchy explanation revealing the exact number, context, and date/match, under 300 characters>",
    "source": "web_search",
    "platform_surface": "{surface_hint}",
    "grounded": true
}}

STRICT SCHEMA RULES:
1. 'target_number' must be a numeric float/integer (e.g. 100, 264, 565, 1994).
2. 'tolerance' must be a number >= 0.0.
3. Do NOT output markdown code formatting outside the JSON.
"""
