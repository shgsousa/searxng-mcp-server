"""
Configuration settings for the SearXNG MCP server.
"""

import os

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
    "server_name": "0.0.0.0",  # Bind to all network interfaces
    "server_port": 7870,       # Default Gradio port
    "share": False,            # Set to True to create a public link
    "auth": None,              # Set to tuple ("username", "password") to enable basic auth
    "mcp": True                # Enable Model Context Protocol (will be converted to mcp_server)
}
