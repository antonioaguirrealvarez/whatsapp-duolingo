"""Web search tool using Firecrawl API."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from src.core.config import get_settings
from src.core.exceptions import LLMError

logger = logging.getLogger(__name__)
settings = get_settings()


class WebSearchTool:
    """Web search tool using Firecrawl API for real-time information."""
    
    def __init__(self):
        """Initialize the web search tool."""
        self.api_key = settings.FIRECRAWL_API_KEY
        self.base_url = "https://api.firecrawl.dev/v0"
        
        if not self.api_key:
            logger.warning("Firecrawl API key not configured - web search disabled")
        else:
            logger.info("Web search tool initialized")
    
    async def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search the web for information.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results
            
        Raises:
            LLMError: If search fails
        """
        if not self.api_key:
            logger.warning("Web search not available - no API key")
            return []
        
        try:
            # Prepare search request
            payload = {
                "query": query,
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyMainContent": True
                },
                "limit": max_results
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Searching web for: {query}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Firecrawl API error: {response.status_code}")
                    return []
                
                data = response.json()
                
                # Extract search results
                results = []
                if "data" in data:
                    for item in data["data"][:max_results]:
                        result = {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("markdown", "")[:500],  # Limit content length
                            "description": item.get("description", ""),
                        }
                        results.append(result)
                
                logger.info(f"Found {len(results)} search results")
                return results
                
        except Exception as e:
            logger.error(f"Error searching web: {e}")
            raise LLMError(f"Failed to search web: {e}")
    
    async def get_page_content(self, url: str) -> Optional[str]:
        """
        Get content from a specific URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Page content as markdown or None if failed
        """
        if not self.api_key:
            logger.warning("Web scraping not available - no API key")
            return None
        
        try:
            payload = {
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": True
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Scraping content from: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/scrape",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Firecrawl scrape error: {response.status_code}")
                    return None
                
                data = response.json()
                
                if "data" in data and "markdown" in data["data"]:
                    content = data["data"]["markdown"]
                    logger.info(f"Successfully scraped {len(content)} characters")
                    return content
                else:
                    logger.warning("No content found in scrape response")
                    return None
                
        except Exception as e:
            logger.error(f"Error scraping page: {e}")
            return None
    
    async def search_slang(
        self, 
        term: str, 
        country: str = "Mexico"
    ) -> List[Dict[str, Any]]:
        """
        Search for current slang usage in a specific country.
        
        Args:
            term: Slang term to search for
            country: Country context for slang
            
        Returns:
            List of slang usage examples
        """
        query = f"{term} slang {country} 2024 meaning usage"
        return await self.search_web(query, max_results=3)
    
    async def search_cultural_context(
        self, 
        topic: str, 
        country: str = "Mexico"
    ) -> List[Dict[str, Any]]:
        """
        Search for cultural context about a topic.
        
        Args:
            topic: Topic to research
            country: Country context
            
        Returns:
            List of cultural context information
        """
        query = f"{topic} culture {country} traditions customs"
        return await self.search_web(query, max_results=3)


# Global web search tool instance
web_search_tool = WebSearchTool()
