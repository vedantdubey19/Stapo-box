"""ChromaDB vector store wrapper for sports knowledge retrieval and deduplication.

Manages:
1. 'sports_facts' collection: pre-seeded knowledge base across all 5 sports.
2. 'generation_history' collection: persistent history of generated items for semantic deduplication.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_FACTS_DIR = PROJECT_ROOT / "data" / "seed_facts"


class VectorStore:
    """Manages on-disk ChromaDB collections and vector similarity queries."""

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
        """Query sports facts filtered by sport and optionally difficulty.

        Args:
            sport: The sport category.
            difficulty: Optional difficulty level (Easy, Medium, Hard).
            query_text: Optional semantic search text. Defaults to sport and difficulty.
            n_results: Max number of facts to return.

        Returns:
            List of dicts containing document text, metadata, and distance score.
        """
        search_text = query_text or f"{difficulty or ''} {sport} sports facts records rules history"
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
                n_results=n_results,
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
                    # Cosine similarity = 1 - cosine distance
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


# Singleton VectorStore instance
vector_store = VectorStore()
