"""
Configuration settings for the SearXNG MCP server.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# SearXNG instance URL (default uses a public instance)
# You can run your own instance using Docker: https://github.com/searxng/searxng-docker
# Read from environment variable if available, otherwise use default
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")

# List of available search engines
SEARCH_ENGINES = [
    "google",
    "bing", 
    "brave", 
    "duckduckgo", 
    "yahoo",
    "qwant",
    "startpage"
]

# Default search engine
DEFAULT_ENGINE = "google"

# Maximum number of results to show in summary mode
MAX_RESULTS = 10
DEFAULT_RESULTS = 5

# Default Gradio server settings
GRADIO_SETTINGS = {
    "server_name": os.environ.get("SERVER_NAME", "0.0.0.0"),  # Bind to all network interfaces
    "server_port": int(os.environ.get("SERVER_PORT", 7870)),  # Default Gradio port
    "share": os.environ.get("SHARE", "false").lower() == "true",  # Set to True to create a public link
    "auth": None,              # Set to tuple ("username", "password") to enable basic auth
    "mcp": os.environ.get("MCP_ENABLED", "true").lower() == "true"  # Enable Model Context Protocol
}

# OpenAI API settings for LLM features
OPENAI_API_URL = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1")
OPENAI_API_TOKEN = os.environ.get("OPENAI_API_TOKEN", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
