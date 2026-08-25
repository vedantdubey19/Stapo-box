"""ChromaDB vector store wrapper for sports knowledge retrieval and deduplication.

Manages:
1. 'sports_facts' collection: pre-seeded knowledge base across all 5 sports.
2. 'generation_history' collection: persistent history of generated items for semantic deduplication.
"""

import json
import logging
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_FACTS_DIR = PROJECT_ROOT / "data" / "seed_facts"


class VectorStore:
    """Manages on-disk ChromaDB collections, vector queries, and semantic deduplication."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self._init_client()
        self._init_collections()
        self.preload_seed_facts()

    def _init_client(self) -> None:
        """Initialize persistent ChromaDB client."""
        persist_path = Path(self.persist_dir)
        persist_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_path))
        logger.info(f"Initialized ChromaDB at {self.persist_dir}")

    def _init_collections(self) -> None:
        """Get or create required collections."""
        self.facts_collection = self.client.get_or_create_collection(
            name="sports_facts",
            metadata={"hnsw:space": "cosine"},
        )
        self.history_collection = self.client.get_or_create_collection(
            name="generation_history",
            metadata={"hnsw:space": "cosine"},
        )

    def preload_seed_facts(self) -> None:
        """Load curated seed facts from data/seed_facts/ into ChromaDB if not already populated."""
        if not SEED_FACTS_DIR.exists():
            logger.warning(f"Seed facts directory not found at {SEED_FACTS_DIR}")
            return

        count = self.facts_collection.count()
        if count > 0:
            logger.info(f"ChromaDB 'sports_facts' already populated with {count} items.")
            return

        documents = []
        metadatas = []
        ids = []

        for json_file in SEED_FACTS_DIR.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    facts = json.load(f)
                    for item in facts:
                        fact_id = item.get("id", f"{item.get('sport')}_{len(ids)}")
                        fact_text = item.get("fact")
                        if fact_text:
                            documents.append(fact_text)
                            metadatas.append({
                                "sport": item.get("sport", ""),
                                "difficulty": item.get("difficulty", "Medium"),
                                "category": item.get("category", "general"),
                            })
                            ids.append(fact_id)
            except Exception as e:
                logger.error(f"Failed to read seed file {json_file}: {e}")

        if documents:
            self.facts_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info(f"Successfully loaded {len(documents)} seed facts into ChromaDB 'sports_facts'.")

    def query_facts(
        self,
        sport: str,
        difficulty: Optional[str] = None,
        query_text: Optional[str] = None,
        n_results: int = 3,
    ) -> List[Dict[str, Any]]:
        """Query sports facts filtered by sport with diverse thematic rotation."""
        angles = [
            "world records and historic milestones",
            "official rules, scoring laws and regulations",
            "legendary champions and tournament history",
            "famous matches and scoring achievements",
            "iconic athletes and record breaking performances",
            "equipment, court dimensions and game tactics",
        ]
        chosen_angle = random.choice(angles)
        search_text = query_text or f"{sport} {difficulty or ''} {chosen_angle}"
        where_filter: Dict[str, Any] = {"sport": sport}
        if difficulty:
            where_filter = {
                "$and": [
                    {"sport": sport},
                    {"difficulty": difficulty},
                ]
            }

        try:
            results = self.facts_collection.query(
                query_texts=[search_text],
                n_results=min(n_results + 2, 6),
                where=where_filter,
            )
            
            # If filtered by difficulty yielded nothing, fallback to sport-only filter
            if not results["documents"] or not results["documents"][0]:
                results = self.facts_collection.query(
                    query_texts=[search_text],
                    n_results=n_results,
                    where={"sport": sport},
                )

            formatted_results = []
            if results["documents"] and results["documents"][0]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
                distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
                
                for doc, meta, dist in zip(docs, metas, distances):
                    sim = 1.0 - dist if dist is not None else 1.0
                    formatted_results.append({
                        "text": doc,
                        "metadata": meta,
                        "similarity": round(sim, 3),
                        "source": "vector_db",
                    })

            return formatted_results
        except Exception as e:
            logger.error(f"VectorStore query_facts error: {e}", exc_info=True)
            return []

    # ── Deduplication / Generation History ──────────────────────────────────────

    def record_generated_item(
        self,
        sport: str,
        content_type: str,
        core_text: str,
        item_id: str,
    ) -> None:
        """Store accepted item core text into persistent ChromaDB generation_history."""
        if not core_text or not core_text.strip():
            return

        try:
            self.history_collection.add(
                documents=[core_text.strip()],
                metadatas=[{
                    "sport": sport,
                    "content_type": content_type,
                    "timestamp": time.time(),
                }],
                ids=[item_id],
            )
            logger.info(f"Recorded item '{item_id}' in generation_history (total: {self.history_collection.count()})")
        except Exception as e:
            logger.error(f"Failed to record item in generation history: {e}")

    def is_duplicate(
        self,
        sport: str,
        content_type: str,
        core_text: str,
        threshold: float = 0.90,
        max_history: int = 50,
    ) -> Tuple[bool, float, Optional[str]]:
        """Check semantic similarity against the last N stored items for sport+type.

        Per Docs/03_RULE_SETS.md §6:
        If cosine similarity > 0.90, flag as duplicate.

        Returns:
            Tuple of (is_duplicate: bool, similarity_score: float, matched_text: Optional[str])
        """
        if not core_text or not core_text.strip():
            return False, 0.0, None

        history_count = self.history_collection.count()
        if history_count == 0:
            return False, 0.0, None

        try:
            n_res = min(history_count, max_history)
            where_filter = {
                "$and": [
                    {"sport": sport},
                    {"content_type": content_type},
                ]
            }

            try:
                results = self.history_collection.query(
                    query_texts=[core_text.strip()],
                    n_results=n_res,
                    where=where_filter,
                )
            except Exception:
                # Fallback to query without metadata filter if filtered query errors
                results = self.history_collection.query(
                    query_texts=[core_text.strip()],
                    n_results=n_res,
                )

            if results["documents"] and results["documents"][0]:
                docs = results["documents"][0]
                distances = results["distances"][0] if results.get("distances") else [1.0] * len(docs)
                
                for doc, dist in zip(docs, distances):
                    similarity = 1.0 - dist if dist is not None else 0.0
                    if similarity >= threshold:
                        logger.warning(
                            f"Semantic duplicate detected! Similarity: {similarity:.3f} >= {threshold}. Matched: '{doc}'"
                        )
                        return True, round(similarity, 3), doc
                
                # Return highest similarity even if under threshold
                best_sim = 1.0 - min(distances) if distances else 0.0
                return False, round(best_sim, 3), docs[0] if docs else None

            return False, 0.0, None
        except Exception as e:
            logger.error(f"Deduplication check error: {e}", exc_info=True)
            return False, 0.0, None


# Singleton VectorStore instance
vector_store = VectorStore()
