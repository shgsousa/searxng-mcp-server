"""
Utility functions for the SearXNG MCP server.
"""

import logging
import requests
from typing import Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup

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
        # Try http first for local/docker instances
        url = 'http://' + url
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    logger.debug(f"Validating SearXNG instance at {url}")
    
    try:
        # Try to access the instance
        try:
            response = requests.get(f"{url}/", timeout=5)
            response.raise_for_status()
            logger.debug(f"Basic connection to {url} successful")
        except Exception as e:
            # If the base URL fails, maybe we need https instead of http
            if url.startswith('http://'):
                https_url = 'https://' + url[7:]
                logger.debug(f"Trying HTTPS URL instead: {https_url}")
                try:
                    response = requests.get(f"{https_url}/", timeout=5)
                    response.raise_for_status()
                    url = https_url
                    logger.debug(f"HTTPS connection successful, using {url}")
                except Exception:
                    # Both failed, report the original error
                    logger.error(f"Failed to connect to {url}: {str(e)}")
                    return False, f"Could not connect to SearXNG instance: {str(e)}"
            else:
                logger.error(f"Failed to connect to {url}: {str(e)}")
                return False, f"Could not connect to SearXNG instance: {str(e)}"
        
        # Check for a simple test search to verify it's actually SearXNG
        # Try both GET and POST methods
        test_successful = False
        error_message = ""
        
        try:
            # Try GET first
            logger.debug(f"Trying GET search to validate {url}")
            test_response = requests.get(f"{url}/search?q=test&format=json", timeout=5)
            test_response.raise_for_status()
            
            # Check if the response has a SearXNG-like structure
            data = test_response.json()
            if 'results' in data:
                logger.info(f"Successfully validated SearXNG instance at {url} via GET")
                test_successful = True
        except Exception as e:
            error_message = f"GET validation failed: {str(e)}"
            logger.debug(error_message)
            
            # If GET fails, try POST
            try:
                logger.debug(f"Trying POST search to validate {url}")
                test_response = requests.post(
                    f"{url}/search", 
                    data={"q": "test", "format": "json"}, 
                    timeout=5
                )
                test_response.raise_for_status()
                
                # Check if the response has a SearXNG-like structure
                data = test_response.json()
                if 'results' in data:
                    logger.info(f"Successfully validated SearXNG instance at {url} via POST")
                    test_successful = True
            except Exception as post_e:
                error_message = f"Both GET and POST validation failed. GET: {str(e)}, POST: {str(post_e)}"
                logger.debug(error_message)
        
        if test_successful:
            logger.info(f"Successfully validated SearXNG instance at {url}")
            return True, url
        else:
            logger.warning(f"URL {url} doesn't appear to be a SearXNG instance")
            return False, "The provided URL doesn't appear to be a SearXNG instance"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to validate SearXNG instance at {url}: {e}")
        return False, f"Could not connect to SearXNG instance: {str(e)}"


def format_error(error_message: str) -> Dict[str, Any]:
    """
    Formats an error message for display in the Gradio interface.
    
    Args:
        error_message: The error message to format
        
    Returns:
        Formatted error message
    """
    detailed_error_message =     f"""
## Error Occurred

{error_message}

### Troubleshooting Steps:

1. Check your internet connection
2. Verify that the SearXNG instance is online and accessible
3. Try using a different search engine or query
4. If using a custom instance, ensure the URL is correct
"""

    return {
        "status": "error",
        "message": error_message,
        "detailed_message": detailed_error_message
    }

def fetch_page_content(url: str) -> Optional[str]:
    headers = {
        'User-Agent': 'Mozilla/5.0'  # Helps avoid getting blocked by some sites
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract just the text content
        return soup.get_text()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
