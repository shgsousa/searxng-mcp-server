# SearXNG MCP Server

A comprehensive Model Context Protocol (MCP) server that provides a powerful Gradio web interface for performing advanced web searches, content scraping, and AI-powered content summarization using SearXNG as the backend.

## Features

### 🔍 Advanced Web Search

- **Multi-Engine Support**: Google, Bing, Brave, DuckDuckGo, Yahoo, and more
- **Flexible Result Formats**:
  - **Summary**: Fast results with titles, URLs, and snippets
  - **Full Content**: Complete webpage content extraction with intelligent filtering  
  - **AI Summary**: AI-generated summaries of full content (requires OpenAI/OpenRouter API)
- **Advanced Filtering**: Time range, language, SafeSearch, and result count controls
- **Custom SearXNG Instance**: Override default instance with your own SearXNG deployment

### 🌐 Web Content Scraping

- **Intelligent Content Extraction**: Automatically filters out navigation, ads, and boilerplate
- **Multi-Site Optimization**: Special handling for Wikipedia, tech blogs, and various website types
- **Markdown Conversion**: Clean, structured markdown output preserving links and formatting  
- **AI Summarization**: Optional AI-powered content summaries

### 🛠 Diagnostics & Utilities

- **Connection Testing**: Comprehensive SearXNG instance diagnostics with troubleshooting tips
- **Date/Time Service**: Current timestamp utility for logging and reference
- **Docker Support**: Complete containerized setup with SearXNG included

### 🤖 MCP Integration

- **API Endpoints**: All functions available via REST API for programmatic access
- **AI System Integration**: MCP-enabled for seamless integration with AI assistants
- **Multi-Tab Interface**: Organized web interface with dedicated sections for each feature

## Setup and Installation

1. Clone the repository:

   ```Powershell
   git clone https://github.com/shgsousa/searxng-mcp-server.git
   cd searxng-mcp-server
   ```

2. Install the required packages (choose one method):

   ```Powershell
   # Using pip with requirements.txt
   pip install -r requirements.txt
   
   # OR using the package setup
   pip install -e .
   ```

3. Run the server:

   ```Powershell
   python main.py
   ```

## Usage

The server provides a comprehensive web interface with multiple tabs for different functionality:

### 🔍 Search Tab

1. Open the Gradio interface in your web browser (default: <http://localhost:7870>)
2. Navigate to the **Search** tab
3. Enter your search query in the text box
4. Select a search engine from the dropdown menu
5. Choose the result format:
   - **Summary**: Fast results with basic information
   - **Full**: Complete webpage content for each result
   - **AI Summary**: AI-generated summaries (requires API key)
6. Configure advanced options (time range, language, SafeSearch, max results)
7. Optionally specify a custom SearXNG instance URL
8. Click **Submit** to perform the search

### 🌐 Web Scraper Tab

1. Navigate to the **Web Scraper** tab  
2. Enter the URL of the webpage you want to scrape
3. Optionally enable **AI Summarization** for condensed content
4. Click **Submit** to extract and process the content

### 🛠 Diagnostics Tab

1. Navigate to the **Diagnostics** tab
2. Optionally enter a custom SearXNG instance URL to test
3. Click **Submit** to run comprehensive connectivity tests
4. Review the detailed diagnostic report and troubleshooting tips

### 🕒 Date & Time Tab

1. Navigate to the **Date & Time** tab
2. Click **Submit** to get the current system date and time

### 🔌 API Access

All functionality is available via REST API endpoints:

- `/api/search` - Web search functionality
- `/api/scrape` - Web content scraping
- `/api/diagnostics` - SearXNG diagnostics  
- `/api/datetime` - Current date/time

## Configuration

The server supports configuration through environment variables or a `.env` file:

### Core Configuration

By default, the MCP server uses a local SearXNG instance at `http://localhost:8080`. To use a different SearXNG instance:

**Option 1: Environment Variable**

```powershell
# On Windows PowerShell
$env:SEARXNG_URL="https://your-searxng-instance.com"
python main.py
```

**Option 2: .env File**

Create a `.env` file in the project root (you can use `.env.example` as a template):

```env
SEARXNG_URL=https://your-searxng-instance.com
```

**Option 3: Direct Configuration**

Edit the `config.py` file:

```python
SEARXNG_URL = "https://your-searxng-instance.com"
```

### AI Features Configuration

AI features (content summarization, enhanced processing) require OpenAI or OpenRouter API credentials:

**OpenAI Configuration:**

```env
OPENAI_API_URL=https://api.openai.com/v1
OPENAI_API_TOKEN=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini  # Optional, defaults to gpt-3.5-turbo
```

**OpenRouter Configuration (Alternative):**

```env
OPENAI_API_URL=https://openrouter.ai/api/v1
OPENAI_API_TOKEN=your_openrouter_api_key_here
OPENAI_MODEL=openai/gpt-4o-mini  # Model format for OpenRouter
```

### Advanced Configuration Options

```env
# Server Configuration
HOST=0.0.0.0              # Gradio server host (default: 127.0.0.1)  
PORT=7870                 # Gradio server port (default: 7870)
MCP_ENABLED=true          # Enable MCP server functionality

# Search Configuration  
MAX_RESULTS=20            # Maximum search results per query
DEFAULT_RESULTS=10        # Default number of results
DEFAULT_ENGINE=google     # Default search engine

# Content Processing
CONTENT_TIMEOUT=30        # Timeout for webpage content fetching (seconds)
SUMMARY_MAX_LENGTH=10000  # Maximum content length for AI summarization
```

### Running SearXNG Locally

The project includes a complete Docker Compose setup that runs both SearXNG and the MCP server:

```bash
docker-compose up -d
```

This will:

1. Start a SearXNG instance at `http://localhost:8080`
2. Start the SearXNG MCP server at `http://localhost:7870`
3. Configure them to work together automatically

The docker-compose.yml file includes all necessary configuration and volume mappings.

## MCP Integration

The server is MCP-enabled through Gradio's launch function, allowing it to be integrated with AI systems as a tool. When `MCP_ENABLED=true` is set in the configuration, the server provides:

- **Standardized Tool Interface**: Compatible with MCP-enabled AI assistants
- **Function Descriptions**: Comprehensive documentation for each available function
- **Type Safety**: Proper parameter validation and error handling
- **Multi-Modal Support**: Text, JSON, and markdown output formats

## Dependencies

### Core Dependencies

- **gradio**: Web interface framework with MCP integration support
- **requests**: HTTP client for API calls and web scraping
- **beautifulsoup4**: HTML parsing and content extraction
- **html2text**: Clean HTML to Markdown conversion
- **python-dotenv**: Environment variable management
- **openai**: AI integration for content summarization (optional)

### Development Dependencies  

- **markdown**: Markdown processing and validation
- **pytest**: Testing framework (for future test development)
- **black**: Code formatting
- **flake8**: Code linting

### Optional Dependencies

- **docker**: For containerized deployment
- **antml-mcp**: Enhanced MCP integration features

## Development

### Running with VS Code Tasks

This project includes VS Code tasks for easy execution:

1. Press `Ctrl+Shift+P` and select "Tasks: Run Task"
2. Select "Run SearXNG MCP Server"

### Docker Support

The project includes Docker Compose support for easy deployment:

**Start all services:**

```bash
docker-compose up -d
```

**Stop all services:**

```bash
docker-compose down
```

**Rebuild after changes:**

```bash
docker-compose up -d --build
```

**View logs:**

```bash
docker-compose logs -f
```

### Local Development Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/shgsousa/searxng-mcp-server.git
   cd searxng-mcp-server
   ```

2. **Install dependencies:**

   ```bash
   # Using pip with requirements.txt
   pip install -r requirements.txt
   
   # OR using the package setup
   pip install -e .
   ```

3. **Configure environment variables:**

   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your preferred settings
   ```

4. **Run the server:**

   ```bash
   python main.py
   ```

### API Documentation

When the server is running, API documentation is automatically available:

- **Interactive Documentation**: Visit `/docs` endpoint for Swagger UI
- **API Schema**: Available at `/api/docs` for programmatic access  
- **OpenAPI Specification**: JSON schema available at `/openapi.json`

### Function Documentation

All major functions include comprehensive docstrings with:

- **Parameter descriptions** with types and constraints
- **Return value specifications** with example structures  
- **Usage examples** for common scenarios
- **Error handling** information and troubleshooting tips
- **Performance considerations** and best practices

## Troubleshooting

### Common Issues

**SearXNG Connection Issues:**

- Use the Diagnostics tab to test your SearXNG instance
- Ensure SearXNG is running and accessible at the configured URL
- Check firewall settings if using custom instances

**AI Summarization Not Working:**

- Verify `OPENAI_API_TOKEN` is set in your environment
- Check `OPENAI_API_URL` points to the correct endpoint  
- Ensure you have sufficient API credits/quota

**Content Scraping Issues:**

- Some websites block automated requests
- Try different user agents or request headers
- Respect robots.txt and website terms of service

**Docker Issues:**

- Ensure Docker and Docker Compose are installed
- Check that ports 7870 and 8080 are available  
- Review container logs with `docker-compose logs`

## License

[MIT License](LICENSE)

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

### Contributing Guidelines

1. **Fork the repository** and create a feature branch
2. **Add tests** for new functionality where applicable  
3. **Update documentation** including docstrings and README
4. **Follow code style** guidelines (use `black` for formatting)
5. **Test thoroughly** with different SearXNG instances and configurations
6. **Submit a pull request** with a clear description of changes

### Development Roadmap

- [ ] Enhanced content filtering and extraction algorithms
- [ ] Support for additional AI providers (Anthropic, Cohere, etc.)  
- [ ] Advanced search result ranking and relevance scoring
- [ ] Built-in caching mechanisms for improved performance
- [ ] WebSocket support for real-time search updates
- [ ] Plugin system for custom content processors
