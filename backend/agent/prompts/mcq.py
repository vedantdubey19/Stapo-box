"""MCQ prompt generation module.

Generates prompt templates specifically tailored for Multiple Choice Questions (MCQ)
with labeled A/B/C/D choices, following Docs/03_RULE_SETS.md §4.
"""

from typing import Optional


def build_prompt(
    sport: str,
    difficulty: str,
    retrieved_context: Optional[str] = None,
    error_feedback: Optional[str] = None,
) -> str:
    """Build a specialized prompt for generating an MCQ sports engagement item.

    Args:
        sport: Selected sport (e.g. Cricket, Football, Tennis).
        difficulty: Difficulty level (Easy, Medium, Hard).
        retrieved_context: Optional factual context retrieved from Web/Vector store.
        error_feedback: Optional feedback from previous validation/grounding retry.

    Returns:
        Structured prompt string for the LLM.
    """
    context_section = ""
    if retrieved_context:
        context_section = f"""
--- CONTEXT ---
{retrieved_context}
--- END CONTEXT ---

CRITICAL GROUNDING RULES:
1. You MUST formulate the question and correct answer using ONLY the verified facts present in the CONTEXT above.
2. The correct answer MUST be directly supported and explicitly identifiable in the context.
3. Do NOT invent, assume, or hallucinate any statistics, names, or numbers not present in the CONTEXT.
"""
    else:
        context_section = """
GROUNDING GUIDELINES:
1. Formulate a 100% factually accurate, verifiable sports trivia question.
2. Ensure the correct answer is indisputably true and widely recognized.
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
Create 1 high-engagement Multiple Choice Question (MCQ) for Instagram Stories/Quiz Stickers.

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
    "question": "<Engaging, clear question text without option prefixes>",
    "options": {{
        "A": "<Option A text>",
        "B": "<Option B text>",
        "C": "<Option C text>",
        "D": "<Option D text>"
    }},
    "correct_answer": "<One of: 'A', 'B', 'C', or 'D'>",
    "explanation": "<Punchy, exciting explanation confirming the fact, under 300 characters>",
    "source": "vector_db",
    "platform_surface": "Story",
    "grounded": true
}}

Ensure all 4 options are plausible, distinct, and concise. Do NOT include Markdown formatting outside the JSON.
"""
