import gradio as gr
import requests
from bs4 import BeautifulSoup
import html2text
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import openai

# Import configuration and utilities
from config import (
    SEARXNG_URL,
    SEARCH_ENGINES,
    DEFAULT_ENGINE,
    MAX_RESULTS,
    DEFAULT_RESULTS,
    GRADIO_SETTINGS,
    OPENAI_API_URL,
    OPENAI_API_TOKEN,
    OPENAI_MODEL
)
from utils import logger, validate_searxng_instance, format_error, fetch_page_content
import copy

# Configure html2text for global use
text_maker = html2text.HTML2Text()
text_maker.ignore_links = False  # Preserve links in the output
text_maker.ignore_images = True  # Skip images to keep the output cleaner

def perform_search(
    query: str, 
    engine: str = DEFAULT_ENGINE, 
    format_type: str = "summary",
    time_range: Optional[str] = None,
    language: str = "all",
    safesearch: str = "Off",
    custom_searxng_url: Optional[str] = None,
    max_results: int = MAX_RESULTS
) -> Dict[str, Any]:
    """
    Perform a comprehensive web search using SearXNG with advanced filtering options.
    
    This function serves as the main search endpoint for the Gradio interface, providing
    flexible search capabilities with multiple output formats and content processing options.
    
    Args:
        query (str): The search terms or question to search for. Cannot be empty.
        engine (str, optional): The search engine backend to use. Defaults to configured 
            DEFAULT_ENGINE. Available options defined in SEARCH_ENGINES config.
        format_type (str, optional): Output format for search results:
            - "summary": Returns basic result information (title, URL, snippet) - fastest
            - "full": Fetches and includes complete webpage content for each result
            - "full_with_ai_summary": Fetches content and replaces with AI-generated summaries
            Defaults to "summary".
        time_range (str, optional): Temporal filter for search results:
            - "day": Results from the last 24 hours
            - "week": Results from the last 7 days  
            - "month": Results from the last 30 days
            - "year": Results from the last 365 days
            - None or "": No time filtering (default)
        language (str, optional): Language code for result filtering. Defaults to "all".
            Supported: "all", "en", "es", "fr", "de", "it", "pt", etc.
        safesearch (str, optional): Content filtering level:
            - "Off": No content filtering (default)  
            - "Moderate": Filter explicit content moderately
            - "Strict": Strict content filtering
        custom_searxng_url (str, optional): Override the default SearXNG instance URL.
            Must be a valid HTTP/HTTPS URL. If provided, the instance will be validated
            before use. Defaults to None (uses configured SEARXNG_URL).
        max_results (int, optional): Maximum number of results to return and process.
            Must be between 1 and MAX_RESULTS. Defaults to MAX_RESULTS config value.
            
    Returns:
        Dict[str, Any]: Search results dictionary containing:
            - For successful searches:
                - "results": List of result dictionaries with title, url, content
                - "number_of_results": Actual count of returned results
                - Additional metadata from SearXNG (query info, suggestions, etc.)
            - For errors:
                - "status": "error"
                - "message": Human-readable error description
                
    Raises:
        No exceptions are raised directly. All errors are caught and returned as 
        error dictionaries in the response.
        
    Examples:
        Basic search:
        >>> perform_search("python programming")
        
        Advanced search with full content:
        >>> perform_search(
        ...     query="machine learning tutorials",
        ...     engine="google", 
        ...     format_type="full",
        ...     time_range="month",
        ...     language="en",
        ...     max_results=5
        ... )
        
    Note:
        - AI summarization requires valid OPENAI_API_TOKEN configuration
        - Full content fetching may be slower due to additional HTTP requests
        - Custom SearXNG URLs are validated for basic connectivity before use
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
        # Try both POST and GET methods
        try:
            response = requests.post(f"{searxng_url}/search", data=params)
            if response.status_code < 200 or response.status_code >= 300:
                # If POST fails, try GET as fallback
                logger.debug(f"POST request failed, trying GET method")
                response = requests.get(f"{searxng_url}/search", params=params)
        except Exception as e:
            # If POST fails completely, try GET
            logger.debug(f"POST request exception: {str(e)}, trying GET method")
            response = requests.get(f"{searxng_url}/search", params=params)
        
        response.raise_for_status()
        results = response.json()
        
        if not results.get("results", []):
            logger.info("Search returned no results")
            return {
                "status": "error",
                "message": "No results found for your query."
            }
        
        # Process results based on format type
        if format_type == "summary":
            return crop_summary_results(results, max_results)
            # return format_summary(results, max_results)
        elif format_type == "full_with_ai_summary":
            return full_content_with_ai_summary(results, max_results)
        else:
            return full_content(results, max_results)
            
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

def crop_summary_results(results: Dict[str, Any], max_results: int = MAX_RESULTS) -> Dict[str, Any]:
    """
    Crop search results to a maximum number of results.
    
    Args:
        results: A dictionary containing search results with a "results" key
        max_results: Maximum number of results to return
        
    Returns:
        Cropped results dictionary
    """
    # First create a deep copy of the original results to avoid modifying it
    cropped_results = copy.deepcopy(results)
    original_count = len(cropped_results.get("results", []))
    # Now limit the results list to max_results
    cropped_results["results"] = cropped_results.get("results", [])[:max_results]
    current_count = len(cropped_results["results"])
    logger.info(f"Cropped results from {original_count} to {current_count} items")
    cropped_results["number_of_results"] = current_count
    return cropped_results

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

def full_content(results: Dict[str, Any], max_results: int) -> Dict[str, Any]:
    """
    Retrieves full content from search results.
    
    Args:
        results: A dictionary containing search results with a "results" key
        
    Returns:
        Formatted string of full content from each URL
    """

    # Generate a full copy of the results to avoid modifying the original
    full_results = copy.deepcopy(results)

    # iterate through the results and fetch full content
    results_count = 0
    for i, result in enumerate(full_results.get("results", []), 1):
        url = result.get("url")
        title = result.get("title", "No title")
        
        # skip results without a URL
        if not url:
            continue

        # fetch the full content for each URL
        content = fetch_page_content(url)
        if not content:
            logger.warning(f"No content retrieved for URL: {url}. Skipping.")
            continue

        # replace the content in the result with the full content
        result["content"] = content

        # Increment the count of results processed
        results_count += 1

        # Stop if we've reached the maximum results limit
        if results_count >= max_results:
            logger.info(f"Reached maximum results limit of {max_results}. Stopping content retrieval.")
            break
    
    # Crop the results to the maximum number of results specified
    full_results["results"] = full_results.get("results", [])[:max_results]
    full_results["number_of_results"] = len(full_results.get("results", []))
    
    return full_results

def full_content_with_ai_summary(results: Dict[str, Any], max_results: int) -> Dict[str, Any]:
    """
    Retrieves content from search results and creates AI-generated summaries without including the original content.
    
    Args:
        results: A dictionary containing search results with a "results" key
        
    Returns:
        Formatted string of AI summaries from each URL
    """
    # Expand the results to full content
    full_results = full_content(results, max_results)
    
    # Create a deep copy to avoid modifying the original results
    summarized_results = copy.deepcopy(full_results)

    for i, result in enumerate(summarized_results.get("results", []), 1):
        # Get the full content for each result
        content = result.get("content", "")
        # Generate AI summary if OpenAI API token is available
        summarized_content = summarize_content(content)
        # replace the content with the AI summary
        result["content"] = summarized_content
    return summarized_results

def extract_web_content(url: str, response: requests.Response) -> tuple[str, Optional[str]]:
    """
    Extract the main content from a webpage, handling special cases like Wikipedia.
    
    Args:
        url: The URL of the webpage
        response: The requests response object containing the page content
        
    Returns:
        A tuple of (extracted_content_as_markdown, page_title)
    """
    # Configure html2text for content extraction
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = False
    text_maker.ignore_images = False
    text_maker.ignore_tables = False
    text_maker.body_width = 0  # Don't wrap text
    
    # Parse and extract text content
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Store the original content length for debugging
    original_length = len(soup.get_text())
    logger.info(f"Original content length before cleanup for {url}: {original_length} characters")
    
    # Copy the soup for diagnostic purposes
    soup_before_cleanup = str(soup)
    
    # Detect the type of website
    is_wikipedia = 'wikipedia.org' in url
    is_tech_blog = any(domain in url for domain in [
        'anthropic.com', 'openai.com', 'ai.meta.com', 'ai.google', 'research.google',
        'github.blog', 'microsoft.com/en-us/research', 'deepmind.com'
    ])
    
    # Clean up the document by removing irrelevant elements
    # Remove unwanted elements that typically contain non-content
    for tag_name in ['script', 'style', 'noscript', 'iframe']:
        for element in soup.select(tag_name):
            element.decompose()
    
    if is_wikipedia:
        # For Wikipedia, we need to be more careful with what we remove
        logger.info(f"Wikipedia page detected: {url}")
        # We'll specifically target known Wikipedia navigation elements
        wiki_noise_selectors = [
            '#mw-navigation', 
            '#mw-panel',
            '#mw-head',
            '.mw-jump-link',
            '.mw-editsection',
            '#mw-page-base',
            '.mw-indicators',
            '#catlinks',
            '.printfooter',
            '.noprint',
            '#footer'
        ]
        
        for selector in wiki_noise_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Avoid removing content - only remove obvious non-content areas
        noise_classes = [
            '.navigation', 
            '.ads', '.ad', '.banner', '.cookie', '.popup',
            '.share', '.comments', '.gdpr', '.promo'
        ]
        
        for selector in noise_classes:
            for element in soup.select(selector):
                element.decompose()
    elif is_tech_blog:
        # For tech blogs like Anthropic, be very conservative in what we remove
        # These sites often have important content in unconventional classes
        logger.info(f"Tech blog/corporate site detected: {url}")
        
        # Only remove the most obvious non-content elements
        minimal_noise_selectors = [
            'nav:not(.article-nav)', # Don't remove article navigation
            'footer',
            '.cookie-banner',
            '.newsletter-signup',
            '.subscribe-form',
            '.gdpr-notice',
            '.popup-overlay'
        ]
        
        for selector in minimal_noise_selectors:
            for element in soup.select(selector):
                element.decompose()
    else:
        # For regular sites, we can be more aggressive
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
                
        # Use partial class selectors only for non-Wikipedia/non-tech-blog sites
        for partial_class in ['menu', 'nav', 'sidebar', 'footer', 'header', 'ad']:
            for element in soup.select(f"[class*={partial_class}]"):
                element.decompose()
    
    # Try to find the main content
    content = None
    content_candidates = []
    
    # For Wikipedia, directly target the content area
    if is_wikipedia:
        wiki_content = soup.select_one('#mw-content-text')
        if wiki_content:
            logger.info(f"Found Wikipedia main content container in {url}")
            content = wiki_content
            max_length = len(content.get_text(strip=True))
        else:
            logger.warning(f"Wikipedia content area not found with selector #mw-content-text in {url}")
    elif is_tech_blog and 'anthropic.com' in url:
        # For Anthropic specifically, look for article tags or main content areas
        anthropic_selectors = [
            'article', 'main', '.content', '.post', '.post-content',
            '.article', '.article-content', '.blog-post', '.page-content'
        ]
        
        for selector in anthropic_selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"Found potential Anthropic content container: {selector}")
            content_candidates.extend(elements)
    else:
        # For other sites, use the general approach
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
    
    # Get the content length after cleanup for debugging
    cleaned_length = len(soup.get_text())
    logger.info(f"Content length after cleanup for {url}: {cleaned_length} characters")
    
    # If we found a good content container, use it. Otherwise, use the filtered body
    if content and max_length > 200:  # Ensure it has adequate text
        logger.info(f"Found main content container in {url} with {max_length} characters")
        text = text_maker.handle(str(content))
        logger.info(f"Extracted text length for {url}: {len(text)} characters")
    else:
        logger.info(f"No main content identified, using filtered page content from {url}")
        # For tech blog sites, try direct body extraction with minimal filtering to avoid missing content
        if is_tech_blog:
            logger.info(f"Using minimal filtering for tech blog content: {url}")
            body = soup.find('body')
            if body:
                text = text_maker.handle(str(body))
                logger.info(f"Tech blog body text length: {len(text)} characters")
            else:
                text = text_maker.handle(str(soup))
        else:
            # For other sites, use the regular approach
            body = soup.find('body')
            if body:
                text = text_maker.handle(str(body))
                logger.info(f"Body text length for {url}: {len(text)} characters")
            else:
                text = text_maker.handle(str(soup))
                logger.info(f"Full page text length for {url}: {len(text)} characters")
        
        # If text is very short, we likely over-filtered - try with original content
        if len(text) < 500:
            logger.warning(f"Content seems over-filtered ({len(text)} chars) for {url}. Using original content.")
            soup = BeautifulSoup(soup_before_cleanup, "html.parser")
            
            if is_wikipedia:
                wiki_content = soup.select_one('#mw-content-text')
                if wiki_content:
                    text = text_maker.handle(str(wiki_content))
                    logger.info(f"Recovered Wikipedia content with {len(text)} characters")
                else:
                    body = soup.find('body')
                    if body:
                        text = text_maker.handle(str(body))
                    else:
                        text = text_maker.handle(str(soup))
            else:
                # For non-Wikipedia sites, minimal filtering approach
                # Just remove scripts and styles
                for tag_name in ['script', 'style']:
                    for element in soup.select(tag_name):
                        element.decompose()
                        
                body = soup.find('body')
                if body:
                    text = text_maker.handle(str(body))
                else:
                    text = text_maker.handle(str(soup))
                    
        # Very last resort - extract with minimal filtering
        if len(text.strip()) < 100:
            logger.warning(f"Still insufficient content ({len(text.strip())} chars) for {url}. Using minimal filtering.")
            simplified_soup = BeautifulSoup(response.text, "html.parser")
            # Just remove scripts and styles
            for tag_name in ['script', 'style']:
                for element in simplified_soup.select(tag_name):
                    element.decompose()
            
            # For Wikipedia, try again to find the content
            if is_wikipedia:
                wiki_content = simplified_soup.select_one('#mw-content-text')
                if wiki_content:
                    text = text_maker.handle(str(wiki_content))
                    logger.info(f"Last-resort Wikipedia extraction found {len(text)} characters")
                else:
                    # Get text from body or whole document
                    body = simplified_soup.find('body')
                    text = text_maker.handle(str(body) if body else str(simplified_soup))
            else:
                # Get text from body or whole document
                body = simplified_soup.find('body')
                text = text_maker.handle(str(body) if body else str(simplified_soup))
            
            logger.info(f"Minimal filtering produced {len(text)} characters for {url}")
    
    title = soup.title.string if soup.title else "No title"
    
    return text, title

def scrape_webpage(url: str, summarize: bool = False) -> Dict[str, Any]:
    """
    Extract and process content from any webpage with optional AI summarization.
    
    This function serves as a web scraping endpoint for the Gradio interface, capable of
    fetching webpage content, cleaning HTML markup, and optionally generating AI summaries.
    The scraper intelligently handles different website types (Wikipedia, tech blogs, etc.)
    to extract the most relevant content while filtering out navigation, ads, and boilerplate.
    
    Args:
        url (str): The target webpage URL to scrape. Can include or omit the protocol
            (https:// will be automatically prepended if missing). Must be a valid,
            accessible web URL.
        summarize (bool, optional): Whether to generate an AI-powered summary of the
            scraped content using the configured OpenAI/OpenRouter API. Defaults to False.
            When True, returns only the AI summary instead of the full content.
            
    Returns:
        Dict[str, Any]: Scraping results dictionary containing:
            - For successful scraping:
                - "url": The final URL that was scraped (with protocol)
                - "summarize": Boolean indicating if summarization was requested
                - "content": The extracted content as formatted markdown text, or
                           AI summary if summarize=True
            - For errors:
                - "status": "error" 
                - "message": Human-readable error description
                
    Content Processing:
        - HTML is converted to clean markdown format preserving structure
        - Scripts, styles, and other non-content elements are removed
        - Navigation, ads, footers, and sidebars are filtered out
        - Special handling for Wikipedia and technical blog sites
        - Links and important formatting are preserved in markdown
        
    AI Summarization:
        - Requires valid OPENAI_API_TOKEN in configuration
        - Generates comprehensive summaries focusing on main ideas
        - Approximately 30% of original length or shorter for very long content
        - Preserves key facts, statistics, and important details
        - Well-structured with appropriate headings
        
    Examples:
        Basic webpage scraping:
        >>> scrape_webpage("https://example.com/article")
        
        Scraping with AI summarization:
        >>> scrape_webpage("https://blog.example.com/long-article", summarize=True)
        
        Auto-protocol handling:
        >>> scrape_webpage("wikipedia.org/wiki/Python")  # https:// added automatically
        
    Note:
        - Some websites may block automated requests or require JavaScript
        - Very large pages may be truncated to avoid excessive processing time
        - AI summarization adds processing time and requires API token configuration
        - The function respects robots.txt where possible but is not guaranteed
    """
    if not url:
        return format_error("No URL provided.")
    
    # Add scheme if missing
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    
    logger.info(f"Scraping webpage: {url}, summarize={summarize}")
    
    page_content = fetch_page_content(url)
    if not page_content:
        error_msg = f"Failed to fetch content from {url}. The page may not exist or is inaccessible."
        logger.error(error_msg)
        return format_error(error_msg)
    if summarize:
        page_content = summarize_content(page_content)
    return {
        "url": url,
        "summarize": summarize,
        "content": page_content
    }

def test_searxng_connection(custom_searxng_url: Optional[str] = None) -> str:
    """
    Perform comprehensive diagnostics on SearXNG instance connectivity and functionality.
    
    This function serves as a diagnostic endpoint for the Gradio interface, testing
    various aspects of SearXNG instance connectivity, API compatibility, and search
    functionality. It provides detailed troubleshooting information to help identify
    and resolve configuration issues.
    
    Args:
        custom_searxng_url (str, optional): Alternative SearXNG instance URL to test
            instead of the default configured instance. Must be a complete URL with
            protocol (e.g., "http://localhost:8080" or "https://searx.example.com").
            If None, tests the SEARXNG_URL from configuration. Defaults to None.
            
    Returns:
        str: Comprehensive diagnostic report as formatted markdown text containing:
            - Test execution timestamp and target URL
            - Basic connectivity test results (HTTP status, headers)
            - GET search functionality test with JSON format validation
            - POST search functionality test  
            - Response structure validation (presence of 'results' key)
            - Detailed troubleshooting tips and common solutions
            - Environment-specific guidance (Docker vs local setup)
            
    Test Coverage:
        1. **Basic Connection**: Tests HTTP connectivity to the root endpoint
           - Validates server is reachable and responding
           - Reports HTTP status code and content type
           
        2. **GET Search Method**: Tests search functionality via GET requests
           - Performs test query with JSON format requirement
           - Validates response structure and JSON parsing
           
        3. **POST Search Method**: Tests search functionality via POST requests  
           - Important for compatibility with different SearXNG configurations
           - Some instances may prefer POST over GET for search requests
           
    Troubleshooting Guidance:
        - Docker networking configuration tips
        - Local development setup verification
        - CORS and firewall issue identification
        - URL format and endpoint validation
        
    Examples:
        Test default configured instance:
        >>> test_searxng_connection()
        
        Test custom instance:
        >>> test_searxng_connection("http://my-searxng:8080")
        
        Test public instance:
        >>> test_searxng_connection("https://searx.example.com")
        
    Note:
        - All network operations have 5-second timeouts to prevent hanging
        - Does not perform actual web searches, only tests API endpoints
        - Results are formatted for easy reading in the Gradio interface
        - Safe to run repeatedly without side effects on the SearXNG instance
    """
    # Use custom URL if provided, otherwise use the configured one
    searxng_url = custom_searxng_url if custom_searxng_url else SEARXNG_URL
    
    logger.info(f"Testing connection to SearXNG instance at: {searxng_url}")
    
    # Prepare diagnostic results
    results = [
        f"# SearXNG Connection Diagnostics\n\n",
        f"**Testing URL**: {searxng_url}\n\n",
        f"**Current time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        "## Test Results\n\n"
    ]
    
    # Test 1: Basic connection test
    try:
        response = requests.get(f"{searxng_url}/", timeout=5)
        response.raise_for_status()
        results.append("✅ **Basic connection**: Success - Server is reachable\n\n")
        results.append(f"   Status code: {response.status_code}\n")
        results.append(f"   Content type: {response.headers.get('Content-Type', 'unknown')}\n\n")
    except requests.exceptions.RequestException as e:
        results.append(f"❌ **Basic connection**: Failed - {str(e)}\n\n")
        results.append("   Try accessing the SearXNG instance directly in your browser to verify it's running.\n\n")
    
    # Test 2: Simple search test
    try:
        # Try GET method
        response = requests.get(f"{searxng_url}/search?q=test&format=json", timeout=5)
        response.raise_for_status()
        results.append("✅ **GET search**: Success\n\n")
        
        # Check if response is valid JSON with expected structure
        try:
            data = response.json()
            if 'results' in data:
                results.append("✅ **JSON format**: Valid SearXNG response structure\n\n")
            else:
                results.append("⚠️ **JSON format**: Unexpected response structure (missing 'results' key)\n\n")
        except json.JSONDecodeError:
            results.append("❌ **JSON format**: Invalid JSON response\n\n")
    except requests.exceptions.RequestException as e:
        results.append(f"❌ **GET search**: Failed - {str(e)}\n\n")
    
    # Test 3: POST search test
    try:
        params = {"q": "test", "format": "json"}
        response = requests.post(f"{searxng_url}/search", data=params, timeout=5)
        response.raise_for_status()
        results.append("✅ **POST search**: Success\n\n")
    except requests.exceptions.RequestException as e:
        results.append(f"❌ **POST search**: Failed - {str(e)}\n\n")
        
    # Add troubleshooting tips
    results.append("## Troubleshooting Tips\n\n")
    results.append("1. **Docker users**: Ensure both containers are running and networked correctly\n")
    results.append("2. **Docker users**: The URL should be `http://searxng:8080` in Docker environment\n")
    results.append("3. **Local setup**: The URL should be `http://localhost:8080` for local development\n")
    results.append("4. **CORS issues**: SearXNG might block requests from different origins\n")
    results.append("5. **Firewall issues**: Check for firewall rules blocking the connection\n")
    
    return "".join(results)

def get_datetime() -> str:
    """
    Retrieve the current system date and time in a human-readable format.
    
    This function serves as a simple utility endpoint for the Gradio interface,
    providing current timestamp information that can be useful for logging,
    timestamping search results, or general reference purposes.
    
    Args:
        None
        
    Returns:
        str: Current date and time formatted as markdown text containing:
            - Day of the week (e.g., "Monday")
            - Month name (e.g., "January") 
            - Day of the month with appropriate suffix
            - Full year (4 digits)
            - Time in 12-hour format with AM/PM designation
            - Formatted with markdown header for display consistency
            
    Format:
        The returned string follows the pattern:
        "## Current Date and Time\n\n{Weekday, Month DD, YYYY HH:MM:SS AM/PM}"
        
    Examples:
        >>> get_datetime()
        "## Current Date and Time\n\nMonday, June 24, 2025 03:45:30 PM"
        
    Note:
        - Uses the system's local timezone setting
        - Time format is consistent with common US conventions (12-hour with AM/PM)
        - Result is formatted as markdown for optimal display in Gradio interface
        - Function execution is logged for debugging purposes
        - Lightweight operation with minimal processing overhead
    """
    now = datetime.now()
    formatted_datetime = now.strftime("%A, %B %d, %Y %I:%M:%S %p")
    logger.info(f"Datetime requested, returning: {formatted_datetime}")
    return f"## Current Date and Time\n\n{formatted_datetime}"

# Define Gradio interface
def create_interface():
    """
    Create and configure the main Gradio interface for SearXNG web search functionality.
    
    This function constructs the primary user interface for the SearXNG MCP server,
    defining all input controls, output formats, and interface configuration. It
    serves as the main entry point for users to interact with the search capabilities
    through a web-based GUI.
    
    Interface Components:
        Input Controls:
            - Search Query: Multi-line text input for search terms
            - Search Engine: Dropdown selector for backend search engines
            - Result Format: Radio buttons for output format selection
            - Time Range: Dropdown for temporal result filtering
            - Language: Dropdown for language-based filtering
            - SafeSearch: Radio buttons for content filtering level
            - Custom SearXNG URL: Optional text input for instance override
            - Max Results: Slider for limiting result count
            
        Output:
            - JSON display of formatted search results with syntax highlighting
            
    Configuration:
        - Title: "SearXNG Search"
        - Theme: Default Gradio theme
        - API Name: "search" (for programmatic access)
        - Comprehensive help documentation and usage examples
        
    Returns:
        gr.Interface: Configured Gradio interface object ready for launching.
            The interface is bound to the perform_search function and includes
            all necessary input validation and output formatting.
            
    Features:
        - Real-time input validation and help text
        - Responsive design adapting to different screen sizes  
        - Detailed usage instructions and examples
        - API endpoint generation for programmatic access
        - Error handling and user-friendly error messages
        
    Usage:
        This function is typically called once during server initialization:
        >>> interface = create_interface()
        >>> interface.launch()
        
    Note:
        - Interface configuration is pulled from GRADIO_SETTINGS and other config values
        - Input validation is handled by the underlying perform_search function
        - The interface supports both interactive web use and API access
        - All search engines and options are dynamically loaded from configuration
    """
    
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
            choices=["summary", "full", "full_with_ai_summary"], 
            value="summary",
            info="Options: Summary for basic info, Full for complete content, Full with AI summary for only AI-generated summaries"
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
    output = gr.JSON(label="Search Results")
    
    # Create the interface
    interface = gr.Interface(
        fn=perform_search,
        inputs=inputs,
        outputs=output,
        title="SearXNG Search",
        description="Search the web using SearXNG with Google as the backend. Get results as summaries, full page content, or AI-generated summaries.",
        theme="default",
        api_name="search",
        article="""
        ## How to use
        1. Enter your search query
        2. Select a search engine
        3. Choose result format:
           - **summary**: Basic information for each result
           - **full**: Complete content from each result page
           - **full_with_ai_summary**: Only AI-generated summaries of the content (no original text)
        4. Adjust advanced options if needed
        5. Click Submit to perform the search
        
        **Note**: The AI summarization feature requires an OpenAI/OpenRouter API token to be configured in the server environment.
        
        This interface is powered by SearXNG, a privacy-respecting metasearch engine.
        """
    )
    
    return interface

def summarize_content(text: str) -> str:
    """
    Summarize the content of a webpage using OpenAI or OpenRouter API
    
    Args:
        text: The text content to summarize
        
    Returns:
        A summarized version of the content
    """
    if not OPENAI_API_TOKEN:
        logger.warning("OpenAI/OpenRouter API token not configured. Summarization unavailable.")
        return text
    
    # Prepare the prompt
    prompt = f"""Please provide a comprehensive summary of the following web content:
The summary should:
1. Focus on the main ideas, findings, and important details
2. Be well-structured with appropriate headings
3. Retain key facts and statistics
4. Be about 30% of the original length (or shorter if the content is very long)
5. Present information in clear, concise language

Here's the content to summarize:

{text[:10000]}  # Limit content to ~10000 chars to avoid token limits
"""

    client = openai.OpenAI(base_url=OPENAI_API_URL, api_key=OPENAI_API_TOKEN)
    
    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes web content accurately and concisely."},
            {"role": "user", "content": prompt}
        ]
    )

    if not completion or not completion.choices or len(completion.choices) == 0:
        logger.error("No valid response from OpenAI/OpenRouter API")
        return text
    else:
        message_content = completion.choices[0].message.content
        if not message_content:
            logger.error("Received empty summary from OpenAI/OpenRouter API")
            return text
        # Strip whitespace and return the summary
        logger.info("AI summarization completed successfully")
        summary = message_content.strip()
        return summary

def main():
    logger.info("Starting SearXNG MCP Server")
    logger.info(f"Using SearXNG instance at: {SEARXNG_URL}")
    logger.info(f"Available search engines: {', '.join(SEARCH_ENGINES)}")
    
    # Extract MCP server setting
    mcp_enabled = GRADIO_SETTINGS.pop('mcp', False)
    
    # Create interfaces
    search_interface = create_interface()
    
    # Create a datetime API endpoint
    datetime_interface = gr.Interface(
        fn=get_datetime,
        inputs=[],
        outputs=gr.Markdown(label="Date and Time"),
        title="SearXNG Date and Time",
        api_name="datetime",
        analytics_enabled=False,
        examples=[],
        cache_examples=False
    )
    
    # Create a diagnostics endpoint
    diagnostics_interface = gr.Interface(
        fn=test_searxng_connection,
        inputs=[
            gr.Textbox(
                label="Custom SearXNG URL (Optional)", 
                placeholder="e.g., http://searxng:8080 or http://localhost:8080",
                info="Leave empty to test the default URL from configuration",
                lines=1
            )
        ],
        outputs=gr.Markdown(label="Diagnostic Results"),
        title="SearXNG Connection Diagnostics",
        description="Test the connection to your SearXNG instance and troubleshoot issues.",
        api_name="diagnostics",
        analytics_enabled=False
    )
    
    # Create a webpage scraper endpoint
    scrape_interface = gr.Interface(
        fn=scrape_webpage,
        inputs=[
            gr.Textbox(
                label="URL", 
                placeholder="Enter webpage URL to scrape",
                lines=1
            ),
            gr.Checkbox(
                label="Summarize Content using AI",
                value=False,
                info="Uses OpenAI/OpenRouter to generate a concise summary"
            )
        ],
        outputs=gr.JSON(label="Scraped Content"),
        title="SearXNG Web Scraper",
        description="Fetch and display content from any webpage.",
        theme="default",
        api_name="scrape",
        article="""
        ## Web Scraper Tool
        
        This tool allows you to fetch and parse content from any webpage.
        
        1. Enter the URL of the webpage to scrape
        2. Optionally enable content summarization with AI
        3. Click Submit to fetch the content
        
        The tool will attempt to extract the main content while removing navigation, ads, and other irrelevant elements.
        
        ### AI Summarization
        When the summarize option is enabled, the tool will use OpenAI or OpenRouter (as configured) to generate a concise 
        summary of the webpage content. This requires an API key to be set in your configuration (OPENAI_API_TOKEN).
        """
    )
    
    # Create a list of demos to display together
    demo = gr.TabbedInterface(
        [search_interface, datetime_interface, scrape_interface, diagnostics_interface],
        ["Search", "Date & Time", "Web Scraper", "Diagnostics"]
    )
    
    # Launch with the mcp_server parameter
    logger.info(f"Launching Gradio server with settings: {GRADIO_SETTINGS}, mcp_server={mcp_enabled}")
    demo.launch(
        **GRADIO_SETTINGS,
        mcp_server=mcp_enabled
    )
    
    logger.info("Gradio server started successfully with search, datetime and scrape endpoints")

if __name__ == "__main__":
    main()
