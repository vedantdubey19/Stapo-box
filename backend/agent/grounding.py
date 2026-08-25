"""Grounding Verification Engine.

Enforces verifiable fact-checking per Docs/03_RULE_SETS.md §5.
Verifies that claimed answers and key statistics exist within the retrieved
evidence context using deterministic substring, fuzzy string matching (RapidFuzz),
and numerical proximity checks.
"""

import re
import logging
from typing import Any, List, Optional, Tuple, Union
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def extract_numbers_from_text(text: str) -> List[float]:
    """Extract all numeric values (integers, floats, formatted numbers) from text.

    Examples: '264 runs', '11 hours', '565 km/h', '199,854 spectators' -> [264.0, 11.0, 565.0, 199854.0]
    """
    cleaned = text.replace(",", "")
    matches = re.findall(r"[-+]?\d*\.?\d+", cleaned)
    numbers = []
    for m in matches:
        try:
            val = float(m)
            numbers.append(val)
        except ValueError:
            continue
    return numbers


def verify_text_grounding(
    claimed_text: str,
    retrieved_context: str,
    threshold: float = 85.0,
) -> Tuple[bool, float, str]:
    """Verify whether a text answer or claim is present in the retrieved context.

    Args:
        claimed_text: The answer string to check (e.g. 'Muttiah Muralitharan').
        retrieved_context: The raw context string from web or vector DB.
        threshold: RapidFuzz score threshold (default: 85.0).

    Returns:
        Tuple of (is_grounded, confidence_score, explanation_str).
    """
    if not claimed_text or not claimed_text.strip():
        return False, 0.0, "Empty claimed answer text."

    if not retrieved_context or not retrieved_context.strip():
        return False, 0.0, "No retrieved context available for verification."

    claim_clean = claimed_text.strip().lower()
    ctx_clean = retrieved_context.strip().lower()

    # Step 1: Direct exact case-insensitive substring match
    if claim_clean in ctx_clean:
        return True, 100.0, f"Exact substring match found in context ('{claimed_text}')."

    # Step 2: Check individual key tokens (e.g., player surnames like 'Lara' in 'Brian Lara')
    words = [w for w in re.split(r"\W+", claim_clean) if len(w) > 2]
    if words and all(w in ctx_clean for w in words):
        return True, 95.0, f"All key tokens present in context: {words}"

    # Step 3: RapidFuzz partial and token set ratio match
    partial_score = fuzz.partial_ratio(claim_clean, ctx_clean)
    token_score = fuzz.token_set_ratio(claim_clean, ctx_clean)
    best_score = max(partial_score, token_score)

    if best_score >= threshold:
        return True, round(float(best_score), 1), f"Fuzzy match passed with score {best_score:.1f}% >= {threshold}%"

    return False, round(float(best_score), 1), f"Claim '{claimed_text}' not verified in context (score {best_score:.1f}% < {threshold}%)"


def verify_numeric_grounding(
    target_number: float,
    retrieved_context: str,
    tolerance_pct: float = 0.02,
) -> Tuple[bool, float, str]:
    """Verify whether a numeric claim appears in the retrieved context.

    Args:
        target_number: The numerical target (e.g. 264.0, 100.0, 565.0).
        retrieved_context: The raw context string.
        tolerance_pct: Acceptable relative deviation (default: 2%).

    Returns:
        Tuple of (is_grounded, confidence_score, explanation_str).
    """
    if not retrieved_context or not retrieved_context.strip():
        return False, 0.0, "No retrieved context available for verification."

    context_numbers = extract_numbers_from_text(retrieved_context)
    if not context_numbers:
        return False, 0.0, "No numbers found in context to match against."

    # Look for exact or proximate numeric match
    for num in context_numbers:
        if num == target_number:
            return True, 100.0, f"Exact numeric match ({target_number}) found in context."
        
        # Check percentage tolerance for floating values
        if target_number != 0:
            diff_pct = abs(num - target_number) / abs(target_number)
            if diff_pct <= tolerance_pct:
                return True, 95.0, f"Proximity numeric match ({num} vs target {target_number}) within {diff_pct*100:.1f}%"

    return False, 0.0, f"Target number {target_number} not found among context numbers: {context_numbers[:10]}"


def verify_grounding(
    claimed_fact: Union[str, float, int],
    retrieved_context: Optional[str],
    content_type: str = "MCQ",
) -> Tuple[bool, float, str]:
    """Main grounding verification dispatch function.

    Args:
        claimed_fact: The correct answer text or target number.
        retrieved_context: The evidence text used to ground the generation.
        content_type: The content type ('MCQ', 'True/False', 'This-or-That', 'Fill in the Blank', 'Guess the Number').

    Returns:
        Tuple of (is_grounded, confidence_score, diagnostic_message).
    """
    # This-or-That is opinion-based and exempt from grounding
    if content_type == "This-or-That":
        return True, 100.0, "This-or-That is opinion-based; grounding exempt."

    if not retrieved_context:
        return False, 0.0, "Missing retrieved context."

    if content_type == "Guess the Number" or isinstance(claimed_fact, (int, float)):
        try:
            val = float(claimed_fact)
            return verify_numeric_grounding(val, retrieved_context)
        except (ValueError, TypeError):
            return verify_text_grounding(str(claimed_fact), retrieved_context)

    return verify_text_grounding(str(claimed_fact), retrieved_context)
