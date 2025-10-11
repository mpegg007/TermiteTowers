<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: infra/mcp/searxng/README.md:97 %
  %ccm_git_author: CCM Maintainer %
  %ccm_git_author_email: ccm@test %
  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
  %ccm_git_commit_id: f8d51ae7fe101541b1ccd2f91922878ece0bb306 %
  %ccm_git_commit_count: 97 %
  %ccm_git_commit_date: 2025-10-10 20:55:46 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: big update %
  %ccm_git_modify_date: 2025-08-29 07:37:53 %
  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_language_mode:  %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 659 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# SearXNG MCP Server

Model Context Protocol server that provides web search capabilities to LLMs via SearXNG.

## Overview

This MCP server enables LLMs (via Open WebUI/Ollama) to perform real-time web searches using the privacy-focused SearXNG metasearch engine running at `http://localhost:3130`.

## Architecture

```
Open WebUI → Ollama → MCP Client → [stdio] → server.py → [HTTP] → SearXNG Container (localhost:3130) → Web Search Results
```

**Key Design Decisions:**
- **stdio transport**: MCP uses stdin/stdout for communication (not HTTP)
- **Host-based**: Runs directly on dev1, not in Docker
- **HTTP client**: Uses requests library to query SearXNG container

## Installation

1. Ensure SearXNG is running:
   ```bash
   docker ps | grep searxng
   curl http://localhost:3130
   ```

2. Install Python dependencies:
   ```bash
   pip install mcp requests
   ```

3. Test the server:
   ```bash
   python server.py
   ```

## Configuration

### For Open WebUI

Add to Open WebUI Admin Settings → External Tools → MCP Servers:

```json
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
```

## Usage

Once configured, LLMs can use the `search_web` tool:

**User:** "What were the Maple Leafs scores yesterday?"

**LLM thinks:** I need current information → uses search_web("Maple Leafs score yesterday")

**MCP Server:** Queries SearXNG → Returns search results

**LLM responds:** "The Maple Leafs won 4-2 against the Canadiens last night. Matthews scored twice..."

## Tools Provided

### `search_web`

Performs a web search via SearXNG.

**Parameters:**
- `query` (string, required): The search query
- `categories` (array, optional): Search categories (general, news, images, etc.)
- `max_results` (integer, optional): Maximum results to return (default: 5)

**Returns:**
- Array of search results with title, url, snippet, and score

## Troubleshooting

**Server won't start:**
- Check Python version: `python --version` (need 3.8+)
- Verify mcp package: `pip list | grep mcp`

**Can't reach SearXNG:**
- Test connectivity: `curl http://localhost:3130`
- Check Docker: `docker ps | grep searxng`

**Open WebUI can't find server:**
- Use absolute path in MCP config
- Check server.py has execute permissions
- Review Open WebUI logs: `docker logs openwebui-dev1`

## Related Documentation

- `/home/mpegg-adm/source/TermiteTowers/wiki/how-to-add-mcp-server.md` - Complete MCP server setup guide
- `/home/mpegg-adm/source/TermiteTowers/infra/docker/searxng-dev1.yml` - SearXNG container config
- `/home/mpegg-adm/source/TermiteTowers/wiki/vision-hal-enterprise-computer.md` - End-state architecture

## Status

- [x] SearXNG container running (port 3130)
- [x] MCP directory structure created
- [ ] server.py implementation
- [ ] Open WebUI MCP configuration
- [ ] End-to-end testing
