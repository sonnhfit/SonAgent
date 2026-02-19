from firecrawl import Firecrawl
from typing import Optional, Dict, Any
import logging
import os


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def crawl_web(url: str) -> str:
    """
    Crawl a webpage and extract its content 

    It returns the structured content of the webpage,
    Parameters
    ----------
    url : str
        The URL of the webpage to crawl. Must be a valid HTTP/HTTPS URL.


    Returns
    -------
    web content of url
    """
    # Initialize Firecrawl client with the API endpoint
    firecrawl_url = os.getenv("FIRECRAWL_URL", "http://103.82.24.113:3002")
    _firecrawl_client = Firecrawl(api_url=firecrawl_url)
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    if not url.startswith(('http://', 'https://')):
        logger.warning(f"URL '{url}' does not start with http:// or https://. Proceeding anyway.")

    try:
        logger.info(f"Crawling URL: {url}")
        result = _firecrawl_client.scrape(url)
        logger.info(f"Successfully crawled {url}")
        raw_content = result.markdown if hasattr(result, 'markdown') else str(result)
        return raw_content
    except Exception as e:
        logger.error(f"Failed to crawl with url {url}: {e}")
        raise