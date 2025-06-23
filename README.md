# SearXNG MCP Server

A Model Context Protocol (MCP) server for SearXNG that provides a Gradio interface for performing web searches with Google as the backend. The server returns either summarized search results or full page content based on user preference.

## Features

- Web search functionality powered by SearXNG
- Multiple search engines support (Google, Bing, Brave, DuckDuckGo, Yahoo)
- Two result formats:
  - **Summary**: Shows a list of search results with titles, URLs, and snippets
  - **Full**: Retrieves and displays the full content of the top result
- MCP-enabled interface for integration with AI systems

## Setup and Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/searxng-mcp-server.git
   cd searxng-mcp-server
   ```

2. Install the required packages:
   ```
   pip install -e .
   ```

3. Run the server:
   ```
   python main.py
   ```

## Usage

1. Open the Gradio interface in your web browser (by default at http://localhost:7860)
2. Enter your search query in the text box
3. Select a search engine from the dropdown menu
4. Choose the result format (summary or full)
5. Click the "Search" button to perform the search

## Configuration

By default, the MCP server uses a public SearXNG instance. To use a different SearXNG instance:

1. Open `main.py`
2. Change the `SEARXNG_URL` variable to your preferred SearXNG instance

## MCP Integration

The server is MCP-enabled through Gradio's launch function, allowing it to be integrated with AI systems as a tool.

## Dependencies

- gradio: Web interface
- requests: HTTP client for API calls
- beautifulsoup4: HTML parsing
- html2text: HTML to Markdown conversion
- markdown: Markdown processing
- antml-mcp: Model Context Protocol integration