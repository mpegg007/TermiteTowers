#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/mcp/searxng/server.py:111 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: e13afb6e37107b0e35f1024d0d6d00a8672256e8 %
#  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
#  %ccm_git_commit_count: 111 %
#  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: docker updates %
#  %ccm_git_modify_date: 2025-10-29 19:12:45 %
#  %ccm_git_file_last_modified: 2025-10-08 20:48:23 %
#  %ccm_git_file_name: server.py %
#  %ccm_git_path: infra/mcp/searxng/server.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 8635 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
SearXNG MCP Server

Model Context Protocol server that provides web search capabilities via SearXNG.
Runs as stdio server for Open WebUI integration.

Usage:
    python server.py

MCP Configuration (for Open WebUI):
    {
      "mcpServers": {
        "searxng": {
          "command": "python",
          "args": ["/home/mpegg-adm/source/TermiteTowers/infra/mcp/searxng/server.py"],
          "env": {
            "SEARXNG_URL": "http://localhost:3130"
          }
        }
      }
    }
"""

import os
import sys
import json
import logging
from typing import Any, Sequence
import requests
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mcp-searxng.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('mcp-searxng')

# Configuration
SEARXNG_URL = os.getenv('SEARXNG_URL', 'http://localhost:3130')
DEFAULT_MAX_RESULTS = 5

# Initialize MCP server
app = Server("searxng")

logger.info(f"SearXNG MCP Server starting (SEARXNG_URL={SEARXNG_URL})")


def search_searxng(query: str, categories: list[str] | None = None, max_results: int = DEFAULT_MAX_RESULTS) -> dict:
    """
    Perform a web search using SearXNG.
    
    Args:
        query: The search query string
        categories: Optional list of categories to search (general, news, images, etc.)
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary with search results or error information
    """
    logger.info(f"Searching SearXNG: query='{query}', categories={categories}, max_results={max_results}")
    
    try:
        # Build request parameters
        params = {
            'q': query,
            'format': 'json',
        }
        
        if categories:
            params['categories'] = ','.join(categories)
        
        # Query SearXNG
        response = requests.get(
            f"{SEARXNG_URL}/search",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        results = data.get('results', [])
        
        # Limit results
        results = results[:max_results]
        
        # Format results
        formatted_results = []
        for idx, result in enumerate(results, 1):
            formatted_results.append({
                'position': idx,
                'title': result.get('title', 'No title'),
                'url': result.get('url', ''),
                'content': result.get('content', result.get('snippet', 'No description')),
                'engine': result.get('engine', 'unknown'),
                'score': result.get('score', 0),
            })
        
        logger.info(f"Found {len(formatted_results)} results for query '{query}'")
        
        return {
            'success': True,
            'query': query,
            'result_count': len(formatted_results),
            'results': formatted_results
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying SearXNG: {e}")
        return {
            'success': False,
            'error': f"Failed to query SearXNG: {str(e)}",
            'query': query,
            'results': []
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}",
            'query': query,
            'results': []
        }


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available MCP tools.
    
    Returns:
        List of Tool objects that LLMs can use
    """
    logger.info("Listing available tools")
    
    return [
        Tool(
            name="search_web",
            description=(
                "Search the web using SearXNG privacy-focused metasearch engine. "
                "Use this tool when you need current information, real-time data, "
                "recent events, news, sports scores, weather, or any information "
                "that requires up-to-date web search. Returns top search results "
                "with titles, URLs, and content snippets."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Be specific and use natural language.",
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional: Search categories to focus on. "
                            "Available: general, news, images, videos, music, files, science, "
                            "it, map, social_media. Default is 'general'."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-20). Default is 5.",
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """
    Handle tool execution requests.
    
    Args:
        name: The tool name to execute
        arguments: Tool-specific arguments
        
    Returns:
        Sequence of content objects with results
    """
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    if name == "search_web":
        query = arguments.get("query")
        if not query:
            error_msg = "Missing required parameter: query"
            logger.error(error_msg)
            return [TextContent(type="text", text=json.dumps({"error": error_msg}))]
        
        categories = arguments.get("categories")
        max_results = arguments.get("max_results", DEFAULT_MAX_RESULTS)
        
        # Validate max_results
        max_results = max(1, min(20, max_results))
        
        # Perform search
        results = search_searxng(query, categories, max_results)
        
        # Format response for LLM
        if results['success']:
            response_text = f"# Web Search Results for: {query}\n\n"
            response_text += f"Found {results['result_count']} results:\n\n"
            
            for result in results['results']:
                response_text += f"## {result['position']}. {result['title']}\n"
                response_text += f"**URL:** {result['url']}\n"
                response_text += f"**Source:** {result['engine']}\n"
                response_text += f"{result['content']}\n\n"
                response_text += "---\n\n"
        else:
            response_text = f"# Search Failed\n\nQuery: {query}\n\nError: {results.get('error', 'Unknown error')}"
        
        return [TextContent(type="text", text=response_text)]
    
    else:
        error_msg = f"Unknown tool: {name}"
        logger.error(error_msg)
        return [TextContent(type="text", text=json.dumps({"error": error_msg}))]


async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting SearXNG MCP Server")
    
    # Test SearXNG connectivity on startup
    try:
        response = requests.get(f"{SEARXNG_URL}/", timeout=5)
        response.raise_for_status()
        logger.info(f"Successfully connected to SearXNG at {SEARXNG_URL}")
    except Exception as e:
        logger.warning(f"Could not connect to SearXNG at {SEARXNG_URL}: {e}")
        logger.warning("Server will start anyway, but searches will fail until SearXNG is available")
    
    # Start stdio server
    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP stdio server running")
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
