"""Phase 0 Connectivity Verification Script.

Tests connectivity and operational readiness for:
1. ChromaDB on-disk vector store
2. Google Gemini LLM API (google-genai SDK)
3. Tavily Web Search API (tavily-python SDK)

Exit code 0 indicates all checks passed successfully.
"""

import sys
import os
import shutil
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings


def test_chromadb_connectivity() -> bool:
    """Verify ChromaDB initialization, document embedding, and querying."""
    print("\n🔍 [1/3] Testing ChromaDB local persistence...")
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        test_dir = PROJECT_ROOT / "data" / "test_chroma"
        if test_dir.exists():
            shutil.rmtree(test_dir)

        client = chromadb.PersistentClient(path=str(test_dir))
        collection = client.get_or_create_collection(name="test_phase0_facts")

        # Insert a sample sports document
        collection.add(
            documents=[
                "Sachin Tendulkar is the first cricketer to score 100 international centuries.",
                "Lionel Messi won the FIFA World Cup with Argentina in 2022.",
            ],
            metadatas=[
                {"sport": "Cricket", "topic": "records"},
                {"sport": "Football", "topic": "records"},
            ],
            ids=["doc_1", "doc_2"],
        )

        # Query the collection
        results = collection.query(
            query_texts=["Who scored 100 international centuries in cricket?"],
            n_results=1,
        )

        assert len(results["documents"][0]) > 0, "No documents returned from query"
        top_doc = results["documents"][0][0]
        assert "Sachin Tendulkar" in top_doc, f"Unexpected top document: {top_doc}"

        # Clean up test directory
        if test_dir.exists():
            shutil.rmtree(test_dir)

        print(f"✅ ChromaDB test passed! Successfully indexed and queried local vector store.")
        return True
    except Exception as e:
        print(f"❌ ChromaDB test failed: {e}")
        return False


def test_gemini_connectivity() -> bool:
    """Verify Google Gemini LLM connectivity using google-genai SDK."""
    print("\n🔍 [2/3] Testing Google Gemini API connectivity...")
    try:
        if not settings.GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY is not set in environment or .env")
            return False

        from google import genai

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Test generation with gemini-2.0-flash
        model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"
        response = client.models.generate_content(
            model=model_name,
            contents="State the country that won the first Cricket World Cup in 1975 in 5 words or less.",
        )

        response_text = response.text.strip() if response.text else ""
        assert len(response_text) > 0, "Gemini returned empty response"

        print(f"✅ Gemini API test passed! Model: {model_name}")
        print(f"   Sample output: \"{response_text}\"")
        return True
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False


def test_tavily_connectivity() -> bool:
    """Verify Tavily Web Search API connectivity using tavily-python SDK."""
    print("\n🔍 [3/3] Testing Tavily Web Search API connectivity...")
    try:
        if not settings.TAVILY_API_KEY:
            print("❌ TAVILY_API_KEY is not set in environment or .env")
            return False

        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(
            query="Who won the latest Wimbledon Men's Singles final?",
            search_depth="basic",
            max_results=2,
        )

        results = response.get("results", [])
        assert len(results) > 0, "Tavily returned no search results"
        
        top_title = results[0].get("title", "No title")
        print(f"✅ Tavily Search API test passed! Returned {len(results)} results.")
        print(f"   Top result: {top_title}")
        return True
    except Exception as e:
        print(f"❌ Tavily API test failed: {e}")
        return False


def main():
    print("=" * 60)
    print("  STAPUBOX SPORTS CONTENT AGENT — PHASE 0 VERIFICATION")
    print("=" * 60)
    print(f"Active LLM Provider: {settings.LLM_PROVIDER}")
    print(f"Active Gemini Model: {settings.GEMINI_MODEL}")
    print(f"ChromaDB Persist Dir: {settings.CHROMA_PERSIST_DIR}")

    chroma_ok = test_chromadb_connectivity()
    gemini_ok = test_gemini_connectivity()
    tavily_ok = test_tavily_connectivity()

    print("\n" + "=" * 60)
    if chroma_ok and gemini_ok and tavily_ok:
        print("🎉 ALL PHASE 0 CONNECTIVITY CHECKS PASSED SUCCESSFULLY!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("⚠️ SOME PHASE 0 CHECKS FAILED. Please review the errors above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
