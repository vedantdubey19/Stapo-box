"""Web Search retrieval module wrapping Tavily Search API."""

import logging
from typing import Any, Dict, List, Optional
from tavily import TavilyClient

from backend.config import settings

logger = logging.getLogger(__name__)


class WebSearch:
    """Tavily search wrapper for real-time and recent sports trivia."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.TAVILY_API_KEY
        self.client: Optional[TavilyClient] = None
        if self.api_key:
            try:
                self.client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize TavilyClient: {e}")

    def search(
        self,
        query: str,
        max_results: int = 3,
        search_depth: str = "basic",
    ) -> List[Dict[str, Any]]:
        """Search the web using Tavily API.

        Args:
            query: Search query string.
            max_results: Maximum number of search results to retrieve.
            search_depth: 'basic' or 'advanced'.

        Returns:
            List of result dicts with keys 'title', 'content', 'url', 'source'.
        """
        if not self.client:
            logger.warning("Tavily client is not initialized or API key is missing.")
            return []

        try:
            logger.info(f"Executing Tavily search for: '{query}'")
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
            )
            raw_results = response.get("results", [])
            formatted = []
            for r in raw_results:
                content = r.get("content", "").strip()
                title = r.get("title", "").strip()
                url = r.get("url", "")
                if content:
                    formatted.append({
                        "title": title,
                        "content": content,
                        "url": url,
                        "source": "web_search",
                    })
            return formatted
        except Exception as e:
            logger.error(f"Tavily search error for query '{query}': {e}", exc_info=True)
            return []


# Singleton WebSearch instance
web_search = WebSearch()
