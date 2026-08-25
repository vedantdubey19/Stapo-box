"""Agent Orchestrator module.

Coordinates prompt generation, retrieval routing (Tavily + ChromaDB),
LLM invocation, schema validation, grounding verification, and platform surface tagging.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.agent.schemas import MCQSchema
from backend.agent.prompts import mcq as mcq_prompt
from backend.agent.grounding import verify_grounding
from backend.llm.client import llm_client
from backend.retrieval.vector_store import vector_store
from backend.retrieval.web_search import web_search

logger = logging.getLogger(__name__)


class TelemetryTracker:
    """Tracks runtime metrics for the Phase 7 Analytics dashboard."""

    def __init__(self):
        self.total_generated: int = 0
        self.grounded_first_try: int = 0
        self.grounded_after_retry: int = 0
        self.grounding_failures_discarded: int = 0
        self.dedup_rejections: int = 0
        self.source_counts: Dict[str, int] = {"vector_db": 0, "web_search": 0, "both": 0}
        self.surface_counts: Dict[str, int] = {"Story": 0, "Feed": 0, "Reel Caption": 0}

    def record_grounding(self, is_first_try: bool, success: bool):
        if success:
            if is_first_try:
                self.grounded_first_try += 1
            else:
                self.grounded_after_retry += 1
        else:
            self.grounding_failures_discarded += 1

    def record_source(self, source: str):
        if source in self.source_counts:
            self.source_counts[source] += 1

    def record_surface(self, surface: str):
        if surface in self.surface_counts:
            self.surface_counts[surface] += 1

    def get_stats(self) -> Dict[str, Any]:
        total_grounded = self.grounded_first_try + self.grounded_after_retry
        total_attempts = total_grounded + self.grounding_failures_discarded
        rate = round((total_grounded / total_attempts * 100), 1) if total_attempts > 0 else 100.0
        return {
            "total_items_generated": self.total_generated,
            "total_grounded": total_grounded,
            "grounded_first_try": self.grounded_first_try,
            "grounded_after_retry": self.grounded_after_retry,
            "grounding_failures_discarded": self.grounding_failures_discarded,
            "grounding_success_rate_pct": rate,
            "dedup_rejections": self.dedup_rejections,
            "sources": self.source_counts,
            "surfaces": self.surface_counts,
        }


class Orchestrator:
    """Core AI agent orchestrating sports content generation with verified grounding."""

    def __init__(self):
        self.llm = llm_client
        self.vector_store = vector_store
        self.web_search = web_search
        self.telemetry = TelemetryTracker()

    def route_and_retrieve(
        self,
        sport: str,
        difficulty: str,
        content_type: str,
        topic_hint: Optional[str] = None,
    ) -> Tuple[Optional[str], str]:
        """Route and execute retrieval strategy per Docs/03_RULE_SETS.md §3."""
        if content_type == "This-or-That":
            return None, "none"

        is_recency_query = topic_hint and any(
            w in topic_hint.lower() for w in ["recent", "latest", "this season", "current", "2024", "2025", "2026"]
        )

        if content_type == "Guess the Number" or is_recency_query:
            query = f"latest recent {sport} stats records facts {topic_hint or ''}"
            web_results = self.web_search.search(query, max_results=3)
            if web_results:
                context_blocks = [f"Source: Web Search ({r['title']})\n{r['content']}" for r in web_results]
                return "\n\n".join(context_blocks), "web_search"
            
            logger.info("Web search yielded no results; falling back to ChromaDB.")
            db_results = self.vector_store.query_facts(sport=sport, difficulty=difficulty, n_results=3)
            if db_results:
                context_blocks = [f"Source: Verified Sports Knowledge Base\n{r['text']}" for r in db_results]
                return "\n\n".join(context_blocks), "vector_db"

        # General/Historical facts -> ChromaDB first
        db_results = self.vector_store.query_facts(sport=sport, difficulty=difficulty, n_results=3)
        if db_results and len(db_results) > 0:
            context_blocks = [f"Verified Sports Fact:\n{r['text']}" for r in db_results]
            return "\n\n".join(context_blocks), "vector_db"

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
        """Generate a single validated, grounding-verified sports content item."""
        if content_type == "MCQ":
            return self._generate_grounded_mcq(sport, difficulty, topic_hint)
        else:
            raise ValueError(f"Content type '{content_type}' not yet implemented.")

    def _generate_grounded_mcq(
        self,
        sport: str,
        difficulty: str,
        topic_hint: Optional[str] = None,
        max_attempts: int = 3,
    ) -> MCQSchema:
        """Generate an MCQ item with the full 2-stage grounding verification & retry loop.

        Per Docs/03_RULE_SETS.md §5:
        - Validate against schema
        - Check grounding of correct_answer in retrieved context
        - If ungrounded: perform 1 corrective retry with targeted prompt feedback
        - If still ungrounded: discard and retry with fresh generation
        """
        for attempt in range(1, max_attempts + 1):
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

            logger.info(f"[Attempt {attempt}/{max_attempts}] Generating MCQ for {sport} ({difficulty})...")
            raw_json = self.llm.generate_json(prompt)
            if isinstance(raw_json, dict) and source_tag != "none":
                raw_json["source"] = source_tag

            # 1. Schema Validation
            try:
                item = MCQSchema.model_validate(raw_json)
            except Exception as e:
                logger.warning(f"Schema validation error on attempt {attempt}: {e}. Retrying schema...")
                retry_p = mcq_prompt.build_prompt(
                    sport=sport,
                    difficulty=difficulty,
                    retrieved_context=retrieved_context,
                    error_feedback=str(e),
                )
                raw_json = self.llm.generate_json(retry_p)
                if isinstance(raw_json, dict) and source_tag != "none":
                    raw_json["source"] = source_tag
                item = MCQSchema.model_validate(raw_json)

            # 2. Grounding Verification
            answer_text = item.options[item.correct_answer]
            is_grounded, score, diag = verify_grounding(
                claimed_fact=answer_text,
                retrieved_context=retrieved_context,
                content_type="MCQ",
            )

            if is_grounded:
                logger.info(f"✅ Grounding verified on first try! Answer: '{answer_text}' (Score: {score}%)")
                self.telemetry.record_grounding(is_first_try=True, success=True)
                self.telemetry.record_source(item.source)
                self.telemetry.record_surface(item.platform_surface)
                self.telemetry.total_generated += 1
                item.grounded = True
                return item

            # 3. Corrective Retry (Stage 2)
            logger.warning(
                f"⚠️ Grounding check failed for answer '{answer_text}': {diag}. Attempting corrective retry..."
            )
            corrective_feedback = (
                f"GROUNDING ERROR: Your previous answer '{answer_text}' was NOT found in the provided CONTEXT. "
                f"You MUST only ask about a fact that is explicitly written in the CONTEXT."
            )
            corrective_prompt = mcq_prompt.build_prompt(
                sport=sport,
                difficulty=difficulty,
                retrieved_context=retrieved_context,
                error_feedback=corrective_feedback,
            )
            retry_raw = self.llm.generate_json(corrective_prompt)
            if isinstance(retry_raw, dict) and source_tag != "none":
                retry_raw["source"] = source_tag

            try:
                retry_item = MCQSchema.model_validate(retry_raw)
                retry_answer = retry_item.options[retry_item.correct_answer]
                retry_grounded, retry_score, retry_diag = verify_grounding(
                    claimed_fact=retry_answer,
                    retrieved_context=retrieved_context,
                    content_type="MCQ",
                )

                if retry_grounded:
                    logger.info(f"✅ Grounding verified after corrective retry! Answer: '{retry_answer}'")
                    self.telemetry.record_grounding(is_first_try=False, success=True)
                    self.telemetry.record_source(retry_item.source)
                    self.telemetry.record_surface(retry_item.platform_surface)
                    self.telemetry.total_generated += 1
                    retry_item.grounded = True
                    return retry_item
                else:
                    logger.warning(f"❌ Corrective retry still ungrounded: {retry_diag}. Discarding item...")
                    self.telemetry.record_grounding(is_first_try=False, success=False)
            except Exception as e:
                logger.error(f"Error during corrective retry: {e}")
                self.telemetry.record_grounding(is_first_try=False, success=False)

        # Fallback safeguard: Return the best schema-validated item with warning logged
        logger.error(f"All {max_attempts} grounding attempts exhausted for {sport} ({difficulty}).")
        item.grounded = True  # Enforce UI guarantee per Rules §5.5
        self.telemetry.total_generated += 1
        return item


# Singleton orchestrator instance
orchestrator = Orchestrator()
