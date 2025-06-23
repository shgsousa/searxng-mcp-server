import gradio as gr
import requests
from bs4 import BeautifulSoup
import html2text
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

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
from utils import logger, validate_searxng_instance, format_error

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
) -> str:
    """
    Perform a search using SearXNG
    
    Args:
        query: The search query
        engine: The search engine to use
        format_type: "summary" for text summary, "full" for full page content, 
                     "full_with_ai_summary" for full page content with AI summarization
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
        # Try both POST and GET methods
        try:
            response = requests.post(f"{searxng_url}/search", data=params)
            if response.status_code != 200:
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
            return "No results found for your query."
        
        # Process results based on format type
        if format_type == "summary":
            return format_summary(results, max_results)
        elif format_type == "full_with_ai_summary":
            # Limit the results before fetching full content to respect max_results
            limited_results = {"results": results.get("results", [])[:max_results]}
            return format_full_content_with_ai_summary(limited_results)
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
    """
    Retrieves full content from search results.
    
    Args:
        results: A dictionary containing search results with a "results" key
        
    Returns:
        Formatted string of full content from each URL
    """
    formatted_results = "# Full Content Results\n\n"

    for i, result in enumerate(results.get("results", []), 1):
        url = result.get("url")
        title = result.get("title", "No title")
        
        if not url:
            formatted_results += f"## Result {i}: Error - No URL\n\n---\n\n"
            continue

        # Add a clear header with result number, title and URL
        formatted_results += f"## Result {i}: {title}\n\n"
        formatted_results += f"**Source URL:** [{url}]({url})\n\n"
        formatted_results += "---\n\n"  # Separator after header info

        logger.info(f"Retrieving full content for URL: {url}")
        try:
            # Fetch the page content with a realistic user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # Use the shared helper function to extract content
            extracted_text, _ = extract_web_content(url, response)
            
            logger.info(f"Successfully retrieved and processed content from {url}")
            formatted_results += f"{extracted_text}\n\n"
            
            # Add a more visible end-of-result separator
            formatted_results += "***\n\n" + "=" * 80 + "\n\n"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving full content from {url}: {e}")
            error_message = f"**Error retrieving full content:** {str(e)}\n\n"
            formatted_results += error_message + "Unable to retrieve full content for this result.\n\n"
            # Add a more visible end-of-result separator even on error
            formatted_results += "***\n\n" + "=" * 80 + "\n\n"
        except Exception as e:
            logger.exception(f"Unexpected error processing content from {url}")
            error_message = f"**Error processing content:** {str(e)}\n\n"
            formatted_results += error_message + "Unable to process content for this result.\n\n"
            # Add a more visible end-of-result separator even on error
            formatted_results += "***\n\n" + "=" * 80 + "\n\n"
    
    return formatted_results

def format_full_content_with_ai_summary(results: Dict[str, Any]) -> str:
    """
    Retrieves content from search results and creates AI-generated summaries without including the original content.
    
    Args:
        results: A dictionary containing search results with a "results" key
        
    Returns:
        Formatted string of AI summaries from each URL
    """
    formatted_results = "# AI-Summarized Search Results\n\n"

    for i, result in enumerate(results.get("results", []), 1):
        url = result.get("url")
        title = result.get("title", "No title")
        
        if not url:
            formatted_results += f"## Result {i}: Error - No URL\n\n---\n\n"
            continue

        # Add a clear header with result number, title and URL
        formatted_results += f"## Result {i}: {title}\n\n"
        formatted_results += f"**Source URL:** [{url}]({url})\n\n"
        formatted_results += "---\n\n"  # Separator after header info

        logger.info(f"Retrieving content for URL: {url}")
        try:
            # Fetch the page content with a realistic user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # Use the shared helper function to extract content
            extracted_text, _ = extract_web_content(url, response)
            
            logger.info(f"Successfully retrieved and processed content from {url}")
            
            # Generate AI summary if OpenAI API token is available
            if OPENAI_API_TOKEN:
                logger.info(f"Generating AI summary for content from {url}")
                ai_summary = summarize_content(extracted_text, title, url)
                formatted_results += ai_summary
            else:
                formatted_results += "### AI Summary Not Available\n\n"
                formatted_results += "**Note:** OpenAI/OpenRouter API token not configured. Please set OPENAI_API_TOKEN in your environment or .env file to enable AI summaries.\n\n"
                formatted_results += "**Content preview:** " + (extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text) + "\n\n"
            
            # Add a more visible end-of-result separator
            formatted_results += "***\n\n" + "=" * 80 + "\n\n"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving full content from {url}: {e}")
            error_message = f"**Error retrieving full content:** {str(e)}\n\n"
            formatted_results += error_message + "Unable to retrieve full content for this result.\n\n"
            # Add a more visible end-of-result separator even on error
            formatted_results += "***\n\n" + "=" * 80 + "\n\n"
        except Exception as e:
            logger.exception(f"Unexpected error processing content from {url}")
            error_message = f"**Error processing content:** {str(e)}\n\n"
            formatted_results += error_message + "Unable to process content for this result.\n\n"
            # Add a more visible end-of-result separator even on error
            formatted_results += "***\n\n" + "=" * 80 + "\n\n"
    
    return formatted_results

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

def scrape_webpage(url: str, summarize: bool = False) -> str:
    """
    Scrapes content from a given URL and returns it as formatted markdown.
    
    Args:
        url: The URL of the webpage to scrape
        summarize: Whether to summarize the content using AI
        
    Returns:
        The webpage content as formatted markdown
    """
    if not url:
        return format_error("No URL provided.")
    
    # Add scheme if missing
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    
    logger.info(f"Scraping webpage: {url}, summarize={summarize}")
    
    try:
        # Fetch the page content with a realistic user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
        }
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        
        # Use the shared helper function to extract content
        extracted_text, title = extract_web_content(url, response)
        title = title if title else "No title"
        
        logger.info(f"Successfully scraped content from {url}")
        
        # If summarize is enabled and we have an API token, summarize the content
        if summarize and OPENAI_API_TOKEN:
            logger.info(f"Summarizing content from {url} using AI")
            return summarize_content(extracted_text, title, url)
        
        # Format the output for non-summarized content
        formatted_content = f"# {title}\n\n"
        formatted_content += f"**Source URL:** {url}\n\n"
        formatted_content += f"**Scraped on:** {datetime.now().strftime('%A, %B %d, %Y %I:%M:%S %p')}\n\n"
        formatted_content += "---\n\n"
        
        # Check if we actually got meaningful content
        if len(extracted_text.strip()) < 100:
            logger.warning(f"Content extraction produced too little text ({len(extracted_text.strip())} chars)")
            formatted_content += "**Note: Content extraction yielded minimal results.**\n\n"
        
        # If summarize was requested but API token is not available
        if summarize and not OPENAI_API_TOKEN:
            formatted_content += "**Note: Content summarization was requested, but no OpenAI/OpenRouter API token is configured.**\n\n"
            formatted_content += "Please set OPENAI_API_TOKEN in your environment or .env file to enable summarization.\n\n"
            
        formatted_content += extracted_text
        
        return formatted_content
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Error retrieving content from {url}: {str(e)}"
        logger.error(error_msg)
        return format_error(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error processing content from {url}: {str(e)}"
        logger.exception("Unexpected error during scraping")
        return format_error(error_msg)

def test_searxng_connection(custom_searxng_url: Optional[str] = None) -> str:
    """
    Test the connection to the SearXNG instance and return diagnostic information.
    
    Args:
        custom_searxng_url: Optional custom SearXNG URL to test
        
    Returns:
        Diagnostic information as a formatted string
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
    Returns the current date and time in a formatted string.
    
    Returns:
        str: Current date and time
    """
    now = datetime.now()
    formatted_datetime = now.strftime("%A, %B %d, %Y %I:%M:%S %p")
    logger.info(f"Datetime requested, returning: {formatted_datetime}")
    return f"## Current Date and Time\n\n{formatted_datetime}"

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
    output = gr.Markdown(label="Search Results")
    
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

def summarize_content(text: str, title: str, url: str) -> str:
    """
    Summarize the content of a webpage using OpenAI or OpenRouter API
    
    Args:
        text: The text content to summarize
        title: The title of the webpage
        url: The URL of the webpage
        
    Returns:
        A summarized version of the content
    """
    if not OPENAI_API_TOKEN:
        logger.warning("OpenAI/OpenRouter API token not configured. Summarization unavailable.")
        return format_error("OpenAI/OpenRouter API token not configured. Please set OPENAI_API_TOKEN in your environment or .env file.")
    
    # Prepare the prompt
    prompt = f"""Please provide a comprehensive summary of the following web content:
Title: {title}
URL: {url}

The summary should:
1. Focus on the main ideas, findings, and important details
2. Be well-structured with appropriate headings
3. Retain key facts and statistics
4. Be about 30% of the original length (or shorter if the content is very long)
5. Present information in clear, concise language

Here's the content to summarize:

{text[:8000]}  # Limit content to ~8000 chars to avoid token limits
"""

    # Determine if we're using OpenRouter based on the API URL
    is_openrouter = "openrouter.ai" in OPENAI_API_URL
    
    # Prepare headers based on the API service
    if is_openrouter:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_TOKEN}",
            "HTTP-Referer": url,  # OpenRouter requires this for attribution
            "X-Title": "SearXNG MCP Server"  # For OpenRouter usage tracking
        }
    else:  # OpenAI
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_TOKEN}"
        }
    
    # Construct the API endpoint
    endpoint = f"{OPENAI_API_URL}/chat/completions"
    
    # Prepare the payload
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that summarizes web content accurately and concisely."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # Lower temperature for more focused summaries
        "max_tokens": 1500  # Reasonable limit for summaries
    }
    
    logger.info(f"Sending summarization request for {url} using model {OPENAI_MODEL}")
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            summary = result["choices"][0]["message"]["content"]
            logger.info(f"Successfully generated summary for {url} ({len(summary)} chars)")
            
            # Format the summary nicely
            formatted_summary = f"# AI-Generated Summary of {title}\n\n"
            formatted_summary += f"**Original URL:** {url}\n\n"
            formatted_summary += f"**Summarized on:** {datetime.now().strftime('%A, %B %d, %Y %I:%M:%S %p')}\n\n"
            formatted_summary += "---\n\n"
            formatted_summary += summary
            formatted_summary += "\n\n---\n\n*Summary generated using AI. Information should be verified from original sources.*\n\n"
            
            return formatted_summary
        else:
            error_msg = f"Invalid response structure from API"
            logger.error(f"{error_msg} for {url}: {result}")
            return format_error(f"Failed to summarize content: {error_msg}")
            
    except requests.exceptions.RequestException as e:
        error_msg = f"API request error: {str(e)}"
        logger.error(f"Summarization failed for {url}: {error_msg}")
        return format_error(f"Failed to summarize content: {error_msg}")
    except json.JSONDecodeError:
        error_msg = "Invalid JSON response from API"
        logger.error(f"Summarization failed for {url}: {error_msg}")
        return format_error(f"Failed to summarize content: {error_msg}")
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"Summarization failed for {url}")
        return format_error(f"Failed to summarize content: {error_msg}")

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
        outputs=gr.Markdown(label="Scraped Content"),
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
