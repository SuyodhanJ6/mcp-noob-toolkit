#!/usr/bin/env python
"""
Jira MCP Server - Provides Jira data extraction services via MCP protocol.
"""

import os
import sys
from typing import Optional, Dict, Any
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport
import uvicorn
import requests

# Load environment variables
load_dotenv()

# Create MCP server
mcp = FastMCP("JiraTools")

class JiraIssueRequest(BaseModel):
    issue_key: str

class JiraIssueResponse(BaseModel):
    summary: str
    description: str
    error: Optional[str] = None

@mcp.tool()
async def extract_jira_issue(request: JiraIssueRequest) -> JiraIssueResponse:
    """
    Extract summary and description from a Jira issue using its key/ID.
    
    Args:
        request: An object containing the Jira issue key.
        
    Returns:
        An object containing the summary, description and any error messages.
    """
    try:
        # Get Jira credentials from environment variables
        # Check for multiple possible environment variable names to be flexible
        jira_base_url = os.getenv("JIRA_BASE_URL") or os.getenv("JIRA_INSTANCE_URL")
        jira_email = os.getenv("JIRA_EMAIL") or os.getenv("JIRA_USERNAME")
        jira_api_token = os.getenv("JIRA_API_TOKEN")
        
        # Print credential information for debugging (without revealing the token)
        print(f"Using Jira credentials - URL: {jira_base_url}, User: {jira_email}")
        
        if not jira_base_url or not jira_email or not jira_api_token:
            missing_vars = []
            if not jira_base_url:
                missing_vars.append("JIRA_BASE_URL/JIRA_INSTANCE_URL")
            if not jira_email:
                missing_vars.append("JIRA_EMAIL/JIRA_USERNAME")
            if not jira_api_token:
                missing_vars.append("JIRA_API_TOKEN")
            
            error_msg = f"Jira credentials not found in environment variables: {', '.join(missing_vars)}"
            print(f"ERROR: {error_msg}")
            return JiraIssueResponse(
                summary="",
                description="",
                error=error_msg
            )
        
        # Construct the API URL
        api_url = f"{jira_base_url}/rest/api/3/issue/{request.issue_key}"
        print(f"Fetching Jira issue from: {api_url}")
        
        # Make the API request
        response = requests.get(
            api_url,
            auth=(jira_email, jira_api_token),
            headers={"Accept": "application/json"}
        )
        
        # Check for errors
        if response.status_code != 200:
            error_msg = f"Failed to fetch Jira issue: {response.status_code} - {response.text}"
            print(f"ERROR: {error_msg}")
            return JiraIssueResponse(
                summary="",
                description="",
                error=error_msg
            )
        
        # Parse the JSON response
        issue_data = response.json()
        
        # Extract the summary and description
        summary = issue_data.get("fields", {}).get("summary", "")
        description = issue_data.get("fields", {}).get("description", "")
        
        # If description is in Atlassian Document Format (ADF), extract the text content
        if isinstance(description, dict) and "content" in description:
            description_text = ""
            for content in description.get("content", []):
                if content.get("type") == "paragraph" and "content" in content:
                    for text_content in content.get("content", []):
                        if text_content.get("type") == "text":
                            description_text += text_content.get("text", "")
                    description_text += "\n"
            description = description_text
        
        print(f"Successfully retrieved Jira issue {request.issue_key}")
        return JiraIssueResponse(
            summary=summary,
            description=description
        )
        
    except Exception as e:
        error_msg = f"Error extracting Jira issue: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        print(traceback.format_exc())
        return JiraIssueResponse(
            summary="",
            description="",
            error=error_msg
        )

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette app with SSE transport for the MCP server."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

def main():
    import argparse

    # Check Jira credentials at startup
    jira_base_url = os.getenv("JIRA_BASE_URL") or os.getenv("JIRA_INSTANCE_URL")
    jira_email = os.getenv("JIRA_EMAIL") or os.getenv("JIRA_USERNAME")
    jira_api_token = os.getenv("JIRA_API_TOKEN")
    
    print("\nJira MCP Server - Credential Check:")
    if jira_base_url:
        print(f"✓ JIRA_BASE_URL/INSTANCE_URL: {jira_base_url}")
    else:
        print("✗ JIRA_BASE_URL/INSTANCE_URL: Not found in environment variables")
        
    if jira_email:
        print(f"✓ JIRA_EMAIL/USERNAME: {jira_email}")
    else:
        print("✗ JIRA_EMAIL/USERNAME: Not found in environment variables")
        
    if jira_api_token:
        print("✓ JIRA_API_TOKEN: Present (not showing for security)")
    else:
        print("✗ JIRA_API_TOKEN: Not found in environment variables")
    
    # Get MCP server instance from FastMCP
    mcp_server = mcp._mcp_server

    parser = argparse.ArgumentParser(description="Jira MCP Server")
    parser.add_argument("--port", type=int, default=3003, help="Port for server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for server")
    
    args = parser.parse_args()
    
    print(f"\nStarting Jira MCP Server on {args.host}:{args.port}")
    
    # Create Starlette app with SSE transport
    starlette_app = create_starlette_app(mcp_server, debug=True)
    
    # Run the server with uvicorn
    uvicorn.run(
        starlette_app,
        host=args.host,
        port=args.port,
    )

if __name__ == "__main__":
    main()
