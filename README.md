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
   git clone https://github.com/shgsousa/searxng-mcp-server.git
   cd searxng-mcp-server
   ```

2. Install the required packages (choose one method):
   ```
   # Using pip with requirements.txt
   pip install -r requirements.txt
   
   # OR using the package setup
   pip install -e .
   ```

3. Run the server:
   ```
   python main.py
   ```

## Usage

1. Open the Gradio interface in your web browser (by default at http://localhost:7870)
2. Enter your search query in the text box
3. Select a search engine from the dropdown menu
4. Choose the result format (summary or full)
5. Click the "Search" button to perform the search

## Configuration

By default, the MCP server uses a local SearXNG instance at http://localhost:8080. To use a different SearXNG instance:

1. Option 1: Set the `SEARXNG_URL` environment variable
   ```
   # On Windows PowerShell
   $env:SEARXNG_URL="https://your-searxng-instance.com"
   python main.py
   ```

2. Option 2: Edit the `config.py` file
   ```python
   SEARXNG_URL = "https://your-searxng-instance.com"
   ```

### Running SearXNG Locally

The project includes a complete Docker Compose setup that runs both SearXNG and the MCP server:

```
docker-compose up -d
```

This will:
1. Start a SearXNG instance at http://localhost:8080
2. Start the SearXNG MCP server at http://localhost:7870
3. Configure them to work together automatically

The docker-compose.yml file includes all necessary configuration and volume mappings.

## MCP Integration

The server is MCP-enabled through Gradio's launch function, allowing it to be integrated with AI systems as a tool.

## Dependencies

- gradio: Web interface with MCP integration
- requests: HTTP client for API calls
- beautifulsoup4: HTML parsing
- html2text: HTML to Markdown conversion
- markdown: Markdown processing
- antml-mcp: Model Context Protocol integration

## Development

### Running with VS Code Tasks

This project includes VS Code tasks for easy execution:

1. Press `Ctrl+Shift+P` and select "Tasks: Run Task"
2. Select "Run SearXNG MCP Server"

### Docker Support

The project includes Docker Compose support for easy deployment:

1. Start both SearXNG and the MCP server with a single command:
   ```
   docker-compose up -d
   ```

2. To stop all services:
   ```
   docker-compose down
   ```

3. To rebuild after making changes:
   ```
   docker-compose up -d --build
   ```

4. To view logs:
   ```
   docker-compose logs -f
   ```

## License

[MIT License](LICENSE)

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.