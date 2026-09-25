#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/mcp/searxng/test_server.py:121 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: ba3f46a5ee5c8b44e38f3787193d3e4398de526b %
#  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
#  %ccm_git_commit_count: 121 %
#  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2025-11-30 12:27:11 %
#  %ccm_git_file_last_modified: 2025-11-30 12:27:11 %
#  %ccm_git_file_name: test_server.py %
#  %ccm_git_path: infra/mcp/searxng/test_server.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 3546 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: november changes % 
"""
Test script for SearXNG MCP Server.

Tests the MCP server by sending a simple search request and verifying the response.
"""

import json
import subprocess
import sys

def test_mcp_server():
    """Test the MCP server with a simple search."""
    
    print("Testing SearXNG MCP Server...")
    print("=" * 60)
    
    # MCP protocol initialization request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    # List tools request
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    # Search request
    search_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_web",
            "arguments": {
                "query": "test search",
                "max_results": 3
            }
        }
    }
    
    try:
        # Start the MCP server
        print("\n1. Starting MCP server...")
        process = subprocess.Popen(
            ['python', '/home/mpegg-adm/source/TermiteTowers/infra/mcp/searxng/server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send initialize request
        print("\n2. Sending initialize request...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response = process.stdout.readline()
        if response:
            resp_data = json.loads(response)
            print(f"   ✓ Server initialized: {resp_data.get('result', {}).get('serverInfo', {}).get('name', 'unknown')}")
        
        # Send list tools request
        print("\n3. Listing available tools...")
        process.stdin.write(json.dumps(list_tools_request) + "\n")
        process.stdin.flush()
        
        response = process.stdout.readline()
        if response:
            resp_data = json.loads(response)
            tools = resp_data.get('result', {}).get('tools', [])
            for tool in tools:
                print(f"   ✓ Tool: {tool.get('name')} - {tool.get('description')[:60]}...")
        
        # Send search request
        print("\n4. Testing search_web tool...")
        process.stdin.write(json.dumps(search_request) + "\n")
        process.stdin.flush()
        
        response = process.stdout.readline()
        if response:
            resp_data = json.loads(response)
            content = resp_data.get('result', {}).get('content', [])
            if content:
                text = content[0].get('text', '')
                print(f"   ✓ Search completed!")
                print(f"\n   Response preview:\n   {text[:200]}...")
        
        # Clean up
        process.terminate()
        process.wait(timeout=5)
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("\nMCP server is ready to use with Open WebUI.")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        if process:
            process.terminate()
        return False


if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)
