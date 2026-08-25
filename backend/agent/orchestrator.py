"""Agent Orchestrator module.

Coordinates prompt generation, LLM invocation, schema validation,
grounding verification, and platform surface tagging.
"""

import logging
from typing import Any, Dict, Optional

from backend.agent.schemas import MCQSchema
from backend.agent.prompts import mcq as mcq_prompt
from backend.llm.client import llm_client

logger = logging.getLogger(__name__)


class Orchestrator:
    """Core AI agent orchestrating sports content generation."""

    def __init__(self):
        self.llm = llm_client

    def generate_single_item(
        self,
        sport: str,
        difficulty: str = "Medium",
        content_type: str = "MCQ",
        retrieved_context: Optional[str] = None,
    ) -> MCQSchema:
        """Generate a single validated sports content item.

        Args:
            sport: The sport (e.g., Cricket, Football).
            difficulty: Difficulty tier (Easy, Medium, Hard).
            content_type: Content format (MCQ, True/False, etc.).
            retrieved_context: Optional factual context for grounding.

        Returns:
            Validated Pydantic model instance.

        Raises:
            ValueError: If an unsupported content type is passed.
            RuntimeError: If generation or validation fails after retries.
        """
        if content_type == "MCQ":
            return self._generate_mcq(sport, difficulty, retrieved_context)
        else:
            raise ValueError(f"Content type '{content_type}' not yet implemented in Phase 1.")

    def _generate_mcq(
        self,
        sport: str,
        difficulty: str,
        retrieved_context: Optional[str] = None,
    ) -> MCQSchema:
        """Generate and validate an MCQ item."""
        prompt = mcq_prompt.build_prompt(
            sport=sport,
            difficulty=difficulty,
            retrieved_context=retrieved_context,
        )

        logger.info(f"Generating MCQ item: sport={sport}, difficulty={difficulty}")
        raw_json = self.llm.generate_json(prompt)
        
        # Schema validation
        try:
            validated_item = MCQSchema.model_validate(raw_json)
            return validated_item
        except Exception as validation_err:
            logger.warning(f"Initial schema validation failed: {validation_err}. Retrying with error feedback...")
            retry_prompt = mcq_prompt.build_prompt(
                sport=sport,
                difficulty=difficulty,
                retrieved_context=retrieved_context,
                error_feedback=str(validation_err),
            )
            retry_json = self.llm.generate_json(retry_prompt)
            validated_item = MCQSchema.model_validate(retry_json)
            return validated_item


# Singleton orchestrator instance
orchestrator = Orchestrator()
