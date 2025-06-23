"""
Utility functions for the SearXNG MCP server.
"""

import logging
import requests
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('searxng-mcp-server')

def validate_searxng_instance(url: str) -> Tuple[bool, str]:
    """
    Validates if the provided URL is a working SearXNG instance.
    
    Args:
        url: The URL of the SearXNG instance to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not url:
        return False, "No URL provided"
    
    # Add scheme if missing
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    try:
        # Try to access the instance
        response = requests.get(f"{url}/", timeout=5)
        response.raise_for_status()
        
        # Check for a simple test search to verify it's actually SearXNG
        test_response = requests.get(f"{url}/search?q=test&format=json", timeout=5)
        test_response.raise_for_status()
        
        # Check if the response has a SearXNG-like structure
        data = test_response.json()
        if 'results' in data:
            logger.info(f"Successfully validated SearXNG instance at {url}")
            return True, url
        else:
            logger.warning(f"URL {url} doesn't appear to be a SearXNG instance")
            return False, "The provided URL doesn't appear to be a SearXNG instance"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to validate SearXNG instance at {url}: {e}")
        return False, f"Could not connect to SearXNG instance: {str(e)}"


def format_error(error_message: str) -> str:
    """
    Formats an error message for display in the Gradio interface.
    
    Args:
        error_message: The error message to format
        
    Returns:
        Formatted error message
    """
    return f"""
## Error Occurred

{error_message}

### Troubleshooting Steps:

1. Check your internet connection
2. Verify that the SearXNG instance is online and accessible
3. Try using a different search engine or query
4. If using a custom instance, ensure the URL is correct
"""
