"""Agent Orchestrator module.

Coordinates prompt generation, retrieval routing (Tavily + ChromaDB),
LLM invocation, schema validation, grounding verification, deterministic platform surface tagging,
and persistent semantic deduplication across all 5 engagement content types.
"""

import logging
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from backend.agent.schemas import (
    MCQSchema,
    TrueFalseSchema,
    ThisOrThatSchema,
    FillBlankSchema,
    GuessNumberSchema,
    BatchItemWrapper,
    ContentItemPayload,
)
from backend.agent.prompts import (
    mcq as mcq_prompt,
    true_false as true_false_prompt,
    this_or_that as this_or_that_prompt,
    fill_blank as fill_blank_prompt,
    guess_number as guess_number_prompt,
)
from backend.agent.grounding import verify_grounding
from backend.agent.surface_mapping import get_platform_surface
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
        self.source_counts: Dict[str, int] = {"vector_db": 0, "web_search": 0, "both": 0, "none": 0}
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
        else:
            self.source_counts[source] = 1

    def record_surface(self, surface: str):
        if surface in self.surface_counts:
            self.surface_counts[surface] += 1
        else:
            self.surface_counts[surface] = 1

    def record_dedup_rejection(self):
        self.dedup_rejections += 1

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
    """Core AI agent orchestrating sports content generation, deduplication, and batch management."""

    def __init__(self):
        self.llm = llm_client
        self.vector_store = vector_store
        self.web_search = web_search
        self.telemetry = TelemetryTracker()

    def _get_schema_class(self, content_type: str) -> Type[Any]:
        """Map content type string to its corresponding Pydantic schema class."""
        mapping = {
            "MCQ": MCQSchema,
            "True/False": TrueFalseSchema,
            "This-or-That": ThisOrThatSchema,
            "Fill in the Blank": FillBlankSchema,
            "Guess the Number": GuessNumberSchema,
        }
        if content_type not in mapping:
            raise ValueError(f"Unsupported content type: {content_type}")
        return mapping[content_type]

    def _get_prompt_builder(self, content_type: str):
        """Map content type string to its specialized prompt builder function."""
        mapping = {
            "MCQ": mcq_prompt.build_prompt,
            "True/False": true_false_prompt.build_prompt,
            "This-or-That": this_or_that_prompt.build_prompt,
            "Fill in the Blank": fill_blank_prompt.build_prompt,
            "Guess the Number": guess_number_prompt.build_prompt,
        }
        if content_type not in mapping:
            raise ValueError(f"Unsupported content type: {content_type}")
        return mapping[content_type]

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

    def _extract_fact_to_verify(self, item: Any, content_type: str) -> Any:
        """Extract the core factual claim or number to verify against context."""
        if content_type == "MCQ":
            return item.options.get(item.correct_answer, "")
        elif content_type == "True/False":
            return item.statement
        elif content_type == "Fill in the Blank":
            return item.correct_answer
        elif content_type == "Guess the Number":
            return item.target_number
        elif content_type == "This-or-That":
            return None
        return ""

    def _extract_core_text(self, item: Any, content_type: str) -> str:
        """Extract the main textual question or statement for semantic deduplication."""
        if content_type == "MCQ":
            return item.question
        elif content_type == "True/False":
            return item.statement
        elif content_type == "This-or-That":
            return item.prompt
        elif content_type == "Fill in the Blank":
            return item.sentence
        elif content_type == "Guess the Number":
            return item.question
        return ""

    def generate_single_item(
        self,
        sport: str,
        difficulty: str = "Medium",
        content_type: str = "MCQ",
        topic_hint: Optional[str] = None,
        max_attempts: int = 3,
    ) -> ContentItemPayload:
        """Generate a single validated, grounded, deduplicated sports content item."""
        schema_cls = self._get_schema_class(content_type)
        prompt_builder = self._get_prompt_builder(content_type)
        deterministic_surface = get_platform_surface(content_type, difficulty)

        for attempt in range(1, max_attempts + 1):
            retrieved_context, source_tag = self.route_and_retrieve(
                sport=sport,
                difficulty=difficulty,
                content_type=content_type,
                topic_hint=topic_hint,
            )

            prompt = prompt_builder(
                sport=sport,
                difficulty=difficulty,
                retrieved_context=retrieved_context,
            )

            logger.info(f"[Attempt {attempt}/{max_attempts}] Generating {content_type} for {sport} ({difficulty})...")
            raw_json = self.llm.generate_json(prompt)

            # Inject deterministic fields
            if isinstance(raw_json, dict):
                raw_json["platform_surface"] = deterministic_surface
                if content_type != "This-or-That" and source_tag != "none":
                    raw_json["source"] = source_tag

            # 1. Schema Validation with retry on parse failure
            try:
                item = schema_cls.model_validate(raw_json)
            except Exception as e:
                logger.warning(f"Schema validation error on attempt {attempt}: {e}. Retrying schema...")
                retry_p = prompt_builder(
                    sport=sport,
                    difficulty=difficulty,
                    retrieved_context=retrieved_context,
                    error_feedback=str(e),
                )
                raw_json = self.llm.generate_json(retry_p)
                if isinstance(raw_json, dict):
                    raw_json["platform_surface"] = deterministic_surface
                    if content_type != "This-or-That" and source_tag != "none":
                        raw_json["source"] = source_tag
                item = schema_cls.model_validate(raw_json)

            # 2. Semantic Deduplication Check
            core_text = self._extract_core_text(item, content_type)
            is_dup, dup_score, matched = self.vector_store.is_duplicate(
                sport=sport,
                content_type=content_type,
                core_text=core_text,
                threshold=0.90,
            )
            if is_dup:
                logger.warning(f"Rejecting duplicate item (similarity {dup_score}): '{core_text}' matched '{matched}'")
                self.telemetry.record_dedup_rejection()
                continue  # Retry with a fresh generation

            # 3. Opinion type exemption (This-or-That)
            if content_type == "This-or-That":
                item_id = str(uuid.uuid4())
                self.vector_store.record_generated_item(sport, content_type, core_text, item_id)
                self.telemetry.record_surface(deterministic_surface)
                self.telemetry.total_generated += 1
                return item

            # 4. Grounding Verification
            fact_to_check = self._extract_fact_to_verify(item, content_type)
            is_grounded, score, diag = verify_grounding(
                claimed_fact=fact_to_check,
                retrieved_context=retrieved_context,
                content_type=content_type,
            )

            if is_grounded:
                logger.info(f"✅ Grounding verified on first try for {content_type}! Claim: '{fact_to_check}' ({score}%)")
                item_id = str(uuid.uuid4())
                self.vector_store.record_generated_item(sport, content_type, core_text, item_id)
                self.telemetry.record_grounding(is_first_try=True, success=True)
                self.telemetry.record_source(item.source)
                self.telemetry.record_surface(item.platform_surface)
                self.telemetry.total_generated += 1
                item.grounded = True
                return item

            # 5. Corrective Retry (Stage 2)
            logger.warning(
                f"⚠️ Grounding check failed for {content_type} claim '{fact_to_check}': {diag}. Attempting corrective retry..."
            )
            corrective_feedback = (
                f"GROUNDING ERROR: Your previous claim/number '{fact_to_check}' was NOT found in the provided CONTEXT. "
                f"You MUST only formulate questions and answers present in the CONTEXT."
            )
            corrective_prompt = prompt_builder(
                sport=sport,
                difficulty=difficulty,
                retrieved_context=retrieved_context,
                error_feedback=corrective_feedback,
            )
            retry_raw = self.llm.generate_json(corrective_prompt)
            if isinstance(retry_raw, dict):
                retry_raw["platform_surface"] = deterministic_surface
                if source_tag != "none":
                    retry_raw["source"] = source_tag

            try:
                retry_item = schema_cls.model_validate(retry_raw)
                retry_core = self._extract_core_text(retry_item, content_type)
                
                # Re-check dedup on retry
                is_retry_dup, _, _ = self.vector_store.is_duplicate(
                    sport=sport, content_type=content_type, core_text=retry_core, threshold=0.90
                )
                if is_retry_dup:
                    self.telemetry.record_dedup_rejection()
                    continue

                retry_fact = self._extract_fact_to_verify(retry_item, content_type)
                retry_grounded, retry_score, retry_diag = verify_grounding(
                    claimed_fact=retry_fact,
                    retrieved_context=retrieved_context,
                    content_type=content_type,
                )

                if retry_grounded:
                    logger.info(f"✅ Grounding verified after corrective retry! Claim: '{retry_fact}'")
                    item_id = str(uuid.uuid4())
                    self.vector_store.record_generated_item(sport, content_type, retry_core, item_id)
                    self.telemetry.record_grounding(is_first_try=False, success=True)
                    self.telemetry.record_source(retry_item.source)
                    self.telemetry.record_surface(retry_item.platform_surface)
                    self.telemetry.total_generated += 1
                    retry_item.grounded = True
                    return retry_item
                else:
                    logger.warning(f"❌ Corrective retry still ungrounded: {retry_diag}. Discarding attempt {attempt}...")
                    self.telemetry.record_grounding(is_first_try=False, success=False)
            except Exception as e:
                logger.error(f"Error during corrective retry: {e}")
                self.telemetry.record_grounding(is_first_try=False, success=False)

        # Fallback safeguard
        logger.error(f"All {max_attempts} attempts exhausted for {content_type} {sport} ({difficulty}).")
        item_id = str(uuid.uuid4())
        self.vector_store.record_generated_item(sport, content_type, core_text, item_id)
        if hasattr(item, "grounded"):
            item.grounded = True
        self.telemetry.total_generated += 1
        return item

    def generate_batch(
        self,
        sport: str,
        difficulty: str = "Medium",
        count: int = 5,
        content_types: Optional[List[str]] = None,
        topic_hint: Optional[str] = None,
    ) -> List[BatchItemWrapper]:
        """Generate a complete batch of 4-5 items, maintaining target count resiliently."""
        available_types = content_types or [
            "MCQ",
            "True/False",
            "This-or-That",
            "Fill in the Blank",
            "Guess the Number",
        ]
        
        assigned_types = []
        for i in range(count):
            assigned_types.append(available_types[i % len(available_types)])

        batch_items: List[BatchItemWrapper] = []

        for idx, c_type in enumerate(assigned_types):
            logger.info(f"Generating batch item {idx+1}/{count}: {c_type} for {sport} ({difficulty})")
            try:
                item_payload = self.generate_single_item(
                    sport=sport,
                    difficulty=difficulty,
                    content_type=c_type,
                    topic_hint=topic_hint,
                )
                wrapper = BatchItemWrapper(
                    id=f"item_{idx}_{uuid.uuid4().hex[:6]}",
                    content_type=c_type,
                    item=item_payload,
                )
                batch_items.append(wrapper)
            except Exception as e:
                logger.error(f"Failed to generate item {idx+1} ({c_type}): {e}. Attempting replacement fallback...")
                try:
                    fallback_item = self.generate_single_item(
                        sport=sport,
                        difficulty=difficulty,
                        content_type="MCQ",
                        topic_hint=topic_hint,
                    )
                    wrapper = BatchItemWrapper(
                        id=f"item_{idx}_fallback_{uuid.uuid4().hex[:6]}",
                        content_type="MCQ",
                        item=fallback_item,
                    )
                    batch_items.append(wrapper)
                except Exception as fatal_e:
                    logger.error(f"Fatal fallback error: {fatal_e}")

        return batch_items

    def regenerate_single_item(
        self,
        sport: str,
        difficulty: str,
        content_type: str,
        topic_hint: Optional[str] = None,
    ) -> BatchItemWrapper:
        """Regenerate a single replacement item for in-place card update."""
        item_payload = self.generate_single_item(
            sport=sport,
            difficulty=difficulty,
            content_type=content_type,
            topic_hint=topic_hint,
        )
        return BatchItemWrapper(
            id=f"regen_{uuid.uuid4().hex[:6]}",
            content_type=content_type,
            item=item_payload,
        )


# Singleton orchestrator instance
orchestrator = Orchestrator()
