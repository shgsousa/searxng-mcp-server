import gradio as gr
import requests
from bs4 import BeautifulSoup
import html2text
import json
import logging
from typing import Dict, Any, List, Optional, Union

# Import configuration and utilities
from config import (
    SEARXNG_URL,
    SEARCH_ENGINES,
    DEFAULT_ENGINE,
    MAX_RESULTS,
    DEFAULT_RESULTS,
    GRADIO_SETTINGS
)
from utils import logger, validate_searxng_instance, format_error

# Configure html2text
text_maker = html2text.HTML2Text()
text_maker.ignore_links = False
text_maker.ignore_images = True

def perform_search(
    query: str, 
    engine: str = DEFAULT_ENGINE, 
    format_type: str = "summary",
    time_range: Optional[str] = None,
    language: str = "all",
    safesearch: str = "Off",
    custom_searxng_url: Optional[str] = None,
    max_results: int = MAX_RESULTS
) -> str:
    """
    Perform a search using SearXNG
    
    Args:
        query: The search query
        engine: The search engine to use
        format_type: "summary" for text summary, "full" for full page content
        time_range: Time range for results (day, week, month, year)
        language: Language filter for results
        safesearch: Safe search level (0=off, 1=moderate, 2=strict)
        custom_searxng_url: Custom SearXNG instance URL (overrides config)
        
    Returns:
        Search results as a formatted string
    """
    # Use custom URL if provided
    searxng_url = custom_searxng_url if custom_searxng_url else SEARXNG_URL
    
    # Validate SearXNG instance if custom URL is provided
    if custom_searxng_url:
        is_valid, result = validate_searxng_instance(custom_searxng_url)
        if not is_valid:
            return format_error(result)
        searxng_url = result  # Use the normalized URL
    
    logger.info(f"Performing search: query='{query}', engine='{engine}', format='{format_type}'")
    
    # Convert safesearch string to integer value
    safesearch_value = {"Off": 0, "Moderate": 1, "Strict": 2}.get(safesearch, 0)
    
    # Prepare search parameters
    params = {
        "q": query,
        "engines": engine,
        "format": "json",  # Use JSON format for API requests
        "safesearch": safesearch_value,
        "language": language
    }
    
    # Add optional time range
    if time_range:
        params["time_range"] = time_range
        logger.debug(f"Added time range filter: {time_range}")
    
    try:
        # Send request to SearXNG
        logger.debug(f"Sending request to {searxng_url}/search with params: {params}")
        response = requests.post(f"{searxng_url}/search", data=params)  # Changed from GET to POST
        response.raise_for_status()
        results = response.json()
        
        if not results.get("results", []):
            logger.info("Search returned no results")
            return "No results found for your query."
        
        # Process results based on format type
        if format_type == "summary":
            return format_summary(results, max_results)
        else:
            # Limit the results before fetching full content to respect max_results
            limited_results = {"results": results.get("results", [])[:max_results]}
            return format_full_content(limited_results)
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Error performing search: {str(e)}"
        logger.error(error_msg)
        return format_error(error_msg)
    except json.JSONDecodeError:
        error_msg = "Error parsing search results. The SearXNG instance returned invalid data."
        logger.error(error_msg)
        return format_error(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception("Unexpected error during search")
        return format_error(error_msg)

def format_summary(results: Dict[str, Any], max_results: int = MAX_RESULTS) -> str:
    """Format search results as a summary"""
    formatted_result = f"Found {len(results.get('results', []))} results:\n\n"
    
    for idx, result in enumerate(results.get("results", []), 1):
        title = result.get("title", "No title")
        url = result.get("url", "")
        content = result.get("content", "No description available.")
        
        formatted_result += f"## {idx}. {title}\n"
        formatted_result += f"URL: {url}\n"
        formatted_result += f"{content}\n\n"
        
        # Limit results according to parameter (defaulting to config value)
        if idx >= max_results:
            break
            
    return formatted_result

def format_full_content(results: Dict[str, Any]) -> str:
    """Format search results with full page content"""
    if not results.get("results", []):
        return "No results found."
    
    formatted_results = "# Full Content Results\n\n"
    
    # Process all results instead of just the first one
    for i, result in enumerate(results.get("results", []), 1):
        title = result.get("title", "No title")
        url = result.get("url", "")
        
        formatted_results += f"## Result {i}: {title}\n\n"
        formatted_results += f"URL: {url}\n\n"
        
        try:
            logger.info(f"Fetching full content from URL: {url}")
            
            # Fetch the page content with a realistic user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # Parse and extract text content
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Clean up the document by removing irrelevant elements
            
            # Remove unwanted elements that typically contain non-content
            for tag_name in ['script', 'style', 'noscript', 'iframe', 'svg']:
                for element in soup.select(tag_name):
                    element.decompose()
                
            # Remove navigation, headers, footers
            for tag_name in ['nav', 'header', 'footer']:
                for element in soup.select(tag_name):
                    element.decompose()
            
            # Remove elements with common noise classes using CSS selectors
            noise_classes = [
                '.menu', '.navbar', '.sidebar', '.footer', '.header', '.navigation', 
                '.ads', '.ad', '.banner', '.cookie', '.popup', '.social', 
                '.share', '.related', '.comments', '.gdpr', '.promo', '.toolbar'
            ]
            
            for selector in noise_classes:
                for element in soup.select(selector):
                    element.decompose()
                    
            # Also try partial class name matches
            for partial_class in ['menu', 'nav', 'sidebar', 'footer', 'header', 'ad']:
                for element in soup.select(f"[class*={partial_class}]"):
                    element.decompose()
            
            # Try to find the main content
            content = None
            content_candidates = []
            
            # Look for common content containers by ID and tag using CSS selectors
            content_selectors = [
                '#content', '#main', '#article', '#post', '.content', '.main', '.article', '.post',
                'article', 'main', 'section.content', 'div.content', 'div.main', 'div.article'
            ]
            
            for selector in content_selectors:
                elements = soup.select(selector)
                content_candidates.extend(elements)
            
            # Find the candidate with the most text content
            max_length = 0
            for candidate in content_candidates:
                try:
                    text = candidate.get_text(strip=True)
                    if len(text) > max_length:
                        content = candidate
                        max_length = len(text)
                except Exception:
                    continue
            
            # If we found a good content container, use it. Otherwise, use the filtered body
            if content and max_length > 200:  # Ensure it has adequate text
                logger.info(f"Found main content container in {url}")
                text = text_maker.handle(str(content))
            else:
                logger.info(f"No main content identified, using filtered page content from {url}")
                # Use the cleaned soup after removing noise
                body = soup.find('body')
                if body:
                    text = text_maker.handle(str(body))
                else:
                    text = text_maker.handle(str(soup))
            
            logger.info(f"Successfully retrieved and processed content from {url}")
            formatted_results += f"{text}\n\n---\n\n"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving full content from {url}: {e}")
            error_message = f"Error retrieving full content: {str(e)}\n\n"
            formatted_results += error_message + "Unable to retrieve full content for this result.\n\n---\n\n"
        except Exception as e:
            logger.exception(f"Unexpected error processing content from {url}")
            error_message = f"Error processing content: {str(e)}\n\n"
            formatted_results += error_message + "Unable to process content for this result.\n\n---\n\n"
    
    return formatted_results

# Define Gradio interface
def create_interface():
    """Create a Gradio Interface for the SearXNG search functionality"""
    
    # Define inputs
    inputs = [
        gr.Textbox(
            label="Search Query", 
            placeholder="Enter your search query here", 
            lines=2
        ),
        gr.Dropdown(
            label="Search Engine", 
            choices=SEARCH_ENGINES, 
            value=DEFAULT_ENGINE
        ),
        gr.Radio(
            label="Result Format", 
            choices=["summary", "full"], 
            value="summary",
            info="Summary shows basic info, Full retrieves complete content for all results"
        ),
        gr.Dropdown(
            label="Time Range", 
            choices=["", "day", "week", "month", "year"], 
            value="", 
            info="Limit results to a specific time period"
        ),
        gr.Dropdown(
            label="Language", 
            choices=["all", "en", "es", "fr", "de", "it", "pt"], 
            value="all",
            info="Filter results by language"
        ),
        gr.Radio(
            label="SafeSearch", 
            choices=["Off", "Moderate", "Strict"],
            value="Off",
            info="Filter explicit content"
        ),
        gr.Textbox(
            label="Custom SearXNG URL (Optional)", 
            placeholder="e.g., https://your-searxng-instance.com",
            info="Override the default SearXNG instance"
        ),
        gr.Slider(
            label="Max Results", 
            minimum=1, 
            maximum=MAX_RESULTS, 
            value=DEFAULT_RESULTS, 
            step=1,
            info="Maximum number of results to display"
        )
    ]
    
    # Define output
    output = gr.Markdown(label="Search Results")
    
    # Create the interface
    interface = gr.Interface(
        fn=perform_search,
        inputs=inputs,
        outputs=output,
        title="SearXNG Search",
        description="Search the web using SearXNG with Google as the backend. Get results as summaries or full page content.",
        theme="default",
        article="""
        ## How to use
        1. Enter your search query
        2. Select a search engine
        3. Choose result format (summary or full)
        4. Adjust advanced options if needed
        5. Click Submit to perform the search
        
        This interface is powered by SearXNG, a privacy-respecting metasearch engine.
        """
    )
    
    return interface

def main():
    logger.info("Starting SearXNG MCP Server")
    logger.info(f"Using SearXNG instance at: {SEARXNG_URL}")
    logger.info(f"Available search engines: {', '.join(SEARCH_ENGINES)}")
    
    # Extract MCP server setting
    mcp_enabled = GRADIO_SETTINGS.pop('mcp', False)
    
    # Create and launch the interface
    interface = create_interface()
    logger.info(f"Launching Gradio server with settings: {GRADIO_SETTINGS}, mcp_server={mcp_enabled}")
    
    # Launch with the mcp_server parameter
    interface.launch(
        **GRADIO_SETTINGS,
        mcp_server=mcp_enabled
    )
    
    logger.info("Gradio server started successfully")

if __name__ == "__main__":
    main()
