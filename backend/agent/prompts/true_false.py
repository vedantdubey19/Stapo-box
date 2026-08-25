"""True/False prompt template module per Docs/03_RULE_SETS.md §4."""

from typing import Optional


def build_prompt(
    sport: str,
    difficulty: str,
    retrieved_context: Optional[str] = None,
    error_feedback: Optional[str] = None,
) -> str:
    """Build a specialized prompt for generating a True/False sports engagement item."""
    context_section = ""
    if retrieved_context:
        context_section = f"""
--- CONTEXT ---
{retrieved_context}
--- END CONTEXT ---

CRITICAL GROUNDING RULES:
1. Formulate the statement based SOLELY on the verified facts in the CONTEXT above.
2. The statement can be factually TRUE (supported by context) or carefully altered to be FALSE (contradicting context).
3. The explanation must clearly reference the verified fact from the CONTEXT.
"""
    else:
        context_section = """
GROUNDING GUIDELINES:
1. Formulate an indisputable, factually verifiable sports statement.
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
Create 1 high-engagement True or False question for Instagram Stories/Polls.

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
    "statement": "<Factual or cleverly false statement for fans to evaluate>",
    "correct_answer": true,
    "explanation": "<Punchy explanation clarifying why it is true or false, under 300 characters>",
    "source": "vector_db",
    "platform_surface": "Story",
    "grounded": true
}}

Ensure correct_answer is a boolean (true or false). Do NOT output markdown code fences outside the JSON.
"""
