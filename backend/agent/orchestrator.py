"""Agent Orchestrator module.

Coordinates prompt generation, retrieval routing (Tavily + ChromaDB),
LLM invocation, schema validation, grounding verification, and platform surface tagging.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.agent.schemas import MCQSchema
from backend.agent.prompts import mcq as mcq_prompt
from backend.llm.client import llm_client
from backend.retrieval.vector_store import vector_store
from backend.retrieval.web_search import web_search

logger = logging.getLogger(__name__)


class Orchestrator:
    """Core AI agent orchestrating sports content generation with hybrid retrieval."""

    def __init__(self):
        self.llm = llm_client
        self.vector_store = vector_store
        self.web_search = web_search

    def route_and_retrieve(
        self,
        sport: str,
        difficulty: str,
        content_type: str,
        topic_hint: Optional[str] = None,
    ) -> Tuple[Optional[str], str]:
        """Route and execute retrieval strategy per Docs/03_RULE_SETS.md §3.

        Returns:
            Tuple of (retrieved_context_text, source_tag)
            where source_tag is 'vector_db', 'web_search', 'both', or 'none'.
        """
        # Rule 1: This-or-That skips retrieval
        if content_type == "This-or-That":
            return None, "none"

        # Rule 2: Guess the Number or recency queries -> Web search first
        is_recency_query = topic_hint and any(
            w in topic_hint.lower() for w in ["recent", "latest", "this season", "current", "2024", "2025", "2026"]
        )

        if content_type == "Guess the Number" or is_recency_query:
            query = f"latest recent {sport} stats records facts {topic_hint or ''}"
            web_results = self.web_search.search(query, max_results=3)
            if web_results:
                context_blocks = [f"Source: Web Search ({r['title']})\n{r['content']}" for r in web_results]
                return "\n\n".join(context_blocks), "web_search"
            # Fallback to vector store if web search returns empty
            logger.info("Web search yielded no results; falling back to ChromaDB.")
            db_results = self.vector_store.query_facts(sport=sport, difficulty=difficulty, n_results=3)
            if db_results:
                context_blocks = [f"Source: Verified Sports Knowledge Base\n{r['text']}" for r in db_results]
                return "\n\n".join(context_blocks), "vector_db"

        # Rule 3: General / Historical facts (MCQ, True/False, FillBlank) -> ChromaDB first
        db_results = self.vector_store.query_facts(sport=sport, difficulty=difficulty, n_results=3)
        
        # Check if vector DB has matching facts for this sport
        if db_results and len(db_results) > 0:
            context_blocks = [f"Verified Sports Fact:\n{r['text']}" for r in db_results]
            return "\n\n".join(context_blocks), "vector_db"

        # Fallback to Web Search if vector store returned no facts for this sport
        logger.info(f"Vector DB has no records for {sport}; falling back to Tavily web search.")
        web_query = f"{difficulty} {sport} trivia facts records history"
        web_results = self.web_search.search(web_query, max_results=2)
        if web_results:
            context_blocks = [f"Source: Web Search ({r['title']})\n{r['content']}" for r in web_results]
            return "\n\n".join(context_blocks), "web_search"

        return None, "vector_db"

    def generate_single_item(
        self,
        sport: str,
        difficulty: str = "Medium",
        content_type: str = "MCQ",
        topic_hint: Optional[str] = None,
    ) -> MCQSchema:
        """Generate a single validated sports content item with hybrid retrieval."""
        if content_type == "MCQ":
            return self._generate_mcq(sport, difficulty, topic_hint)
        else:
            raise ValueError(f"Content type '{content_type}' not yet implemented.")

    def _generate_mcq(
        self,
        sport: str,
        difficulty: str,
        topic_hint: Optional[str] = None,
    ) -> MCQSchema:
        """Generate and validate an MCQ item using retrieved context."""
        retrieved_context, source_tag = self.route_and_retrieve(
            sport=sport,
            difficulty=difficulty,
            content_type="MCQ",
            topic_hint=topic_hint,
        )

        prompt = mcq_prompt.build_prompt(
            sport=sport,
            difficulty=difficulty,
            retrieved_context=retrieved_context,
        )

        logger.info(f"Generating MCQ item: sport={sport}, difficulty={difficulty}, source={source_tag}")
        raw_json = self.llm.generate_json(prompt)
        
        # Inject retrieved source tag into raw JSON if LLM omitted or defaulted
        if isinstance(raw_json, dict) and source_tag != "none":
            raw_json["source"] = source_tag

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
            if isinstance(retry_json, dict) and source_tag != "none":
                retry_json["source"] = source_tag
            validated_item = MCQSchema.model_validate(retry_json)
            return validated_item


# Singleton orchestrator instance
orchestrator = Orchestrator()
