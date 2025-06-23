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

You can run your own SearXNG instance using Docker:
```
docker-compose up -d
```

This will start a local SearXNG instance at http://localhost:8080 using the included docker-compose.yml file.

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

The project includes Docker support for easy deployment:

1. Build the Docker image:
   ```
   docker build -t searxng-mcp-server .
   ```

2. Run the container:
   ```
   docker run -p 7870:7870 searxng-mcp-server
   ```

## License

[MIT License](LICENSE)

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.