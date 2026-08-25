"""This-or-That prompt template module per Docs/03_RULE_SETS.md §4.

Opinion-based debate poll. Does NOT use retrieval, correct_answer, or grounded fields.
"""

from typing import Optional


def build_prompt(
    sport: str,
    difficulty: str = "Medium",
    retrieved_context: Optional[str] = None,
    error_feedback: Optional[str] = None,
) -> str:
    """Build a specialized prompt for generating a This-or-That sports debate poll."""
    retry_section = ""
    if error_feedback:
        retry_section = f"""
PREVIOUS ATTEMPT FAILED WITH ERROR:
{error_feedback}
Please fix this issue in your new response.
"""

    return f"""You are an elite sports social media strategist creating viral Instagram Story polls.

TASK:
Create 1 high-engagement "This or That" debate poll for Instagram Stories (native Poll sticker).

TARGET SPECIFICATIONS:
- Sport: {sport}
- Topic Style: An intense, passionate, highly debatable comparison between two iconic players, moments, eras, or iconic plays.
- STRICT RULE: This is an OPINION poll. There is NO factual correct answer. Both options must be compelling and spark fierce debate among fans.

{retry_section}
FORMAT REQUIREMENTS:
Return a single JSON object with EXACTLY the following keys:
{{
    "sport": "{sport}",
    "prompt": "<Engaging debate prompt, e.g. 'Prime CR7 (2012) vs Prime Messi (2012): Who was more unstoppable?'>",
    "options": [
        "<Option 1 Name/Style>",
        "<Option 2 Name/Style>"
    ],
    "is_opinion": true,
    "platform_surface": "Story"
}}

STRICT SCHEMA RULES:
1. 'options' must be a list containing EXACTLY 2 distinct choices.
2. 'is_opinion' must be set to true.
3. Do NOT include 'correct_answer', 'explanation', 'source', or 'grounded' fields.
4. Do NOT output markdown formatting outside the JSON.
"""
