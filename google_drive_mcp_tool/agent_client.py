#!/usr/bin/env python3
"""
Google Drive MCP Agent Client - Simple client for Google Drive operations through MCP
"""

import os
import asyncio
import argparse
import logging
import logging.config
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configurations
from config import (
    LOGGING_CONFIG,
    DEFAULT_MODEL,
    DEFAULT_MAX_RESULTS,
    SYSTEM_PROMPTS,
    ERROR_MESSAGES,
    DRIVE_MCP_URL
)

# LangChain MCP adapter imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('gdrive_mcp_agent')

# Google Drive Assistant Agent Prompt
GDRIVE_AGENT_PROMPT = """
You are a helpful Google Drive assistant with the following capabilities:

1. FILE MANAGEMENT:
   - GoogleDriveTools.list_drive_files: List files in Google Drive
   - GoogleDriveTools.get_file_metadata: Get metadata for a specific file
   - GoogleDriveTools.download_drive_file: Download a file from Google Drive
   - GoogleDriveTools.upload_file_to_drive: Upload a file to Google Drive
   - GoogleDriveTools.delete_drive_file: Delete a file from Google Drive
   - GoogleDriveTools.move_drive_file: Move a file to a different folder

2. DOCUMENT CREATION:
   - GoogleDriveTools.create_drive_document: Create a new Google Docs document
   - GoogleDriveTools.create_drive_spreadsheet: Create a new Google Sheets spreadsheet
   - GoogleDriveTools.create_drive_presentation: Create a new Google Slides presentation
   - GoogleDriveTools.create_drive_folder: Create a new folder in Google Drive

3. DOCUMENT CONTENT EDITING:
   - GoogleDriveTools.get_document_content_tool: Get the content of a Google Docs document
   - GoogleDriveTools.update_document_content_tool: Edit the content of a Google Docs document
   - GoogleDriveTools.get_spreadsheet_content_tool: Get the content of a Google Sheets spreadsheet
   - GoogleDriveTools.update_spreadsheet_content_tool: Edit the structure of a Google Sheets spreadsheet
   - GoogleDriveTools.update_spreadsheet_values_tool: Update values in a Google Sheets spreadsheet
   - GoogleDriveTools.get_presentation_content_tool: Get the content of a Google Slides presentation
   - GoogleDriveTools.update_presentation_content_tool: Edit the content of a Google Slides presentation

4. COLLABORATION:
   - GoogleDriveTools.share_drive_file: Share a file with another user

5. AUTHENTICATION:
   - GoogleDriveTools.authenticate_drive: Authenticate with Google Drive

Analyze the user's query to determine which tool to use:

- For VIEWING FILES: Use list_drive_files to search for files
  Examples: "Show me my recent files", "List my PDF files", "Search for documents containing 'quarterly report'"

- For FILE DETAILS: Use get_file_metadata to get information about a specific file
  Examples: "What's the size of file X?", "When was document Y created?", "Show details of my presentation"

- For DOWNLOADING FILES: Use download_drive_file to retrieve files
  Examples: "Download my quarterly report", "Get my latest presentation", "Download my budget spreadsheet as Excel"

- For UPLOADING FILES: Use upload_file_to_drive to add files to Drive
  Examples: "Upload report.pdf to Drive", "Upload my image to the Photos folder", "Add this document to Drive"

- For MOVING FILES: Use move_drive_file to relocate files between folders
  Examples: "Move my report.pdf to the Archive folder", "Put this spreadsheet in my Projects folder"
  Examples: "Transfer my presentation to the Shared folder", "Move these documents to my Work folder"

- For DOCUMENT CREATION: Use appropriate creation tools
  Examples: "Create a new document called 'Meeting Notes'", "Make a presentation about climate change"
  Examples: "Create a spreadsheet for budget tracking", "Create a new folder for project files"

- For DOCUMENT EDITING: Use content editing tools to modify documents
  Examples: "Add a new paragraph to my document", "Update cell A1 with value 100 in my spreadsheet"
  Examples: "Add a new slide to my presentation", "Change the title of my document to 'Final Report'"
  Examples: "Insert a table in my document", "Read the content of my presentation"
  Examples: "Update the values in range A1:B10 in my spreadsheet"
  Examples: "Format the text in my document to be bold", "Add bullet points to my presentation"

- For SHARING: Use share_drive_file to set permissions
  Examples: "Share my report with john@example.com", "Make my presentation viewable by anyone with the link"
  Examples: "Give edit access to my team members", "Let marketing@company.com comment on my document"

When working with files, you might need to first search for the file to get its ID, and then perform operations on it.
For shared files or public files, you'll need the file ID to access them.

For document operations that require specific formats (like Google Docs API or Google Sheets API requests), 
you can help the user construct the proper request format. For example, to update a document with the 
update_document_content_tool, you need to provide a list of request objects that follow the Google Docs API format.

For complex document management tasks, break them down into sequential steps:
1. Search for relevant files
2. Get the content of the document to understand its structure
3. Create the appropriate update requests
4. Apply the updates
5. Share the updated documents if needed

Always respond in a clear, concise, and helpful manner. Ask for clarification if
the user's request is ambiguous or lacks necessary details.
"""

async def run_gdrive_agent(query: str, model_name: str = DEFAULT_MODEL) -> None:
    """
    Run the Google Drive Agent with the provided query
    
    Args:
        query: Natural language query
        model_name: LLM model to use
    """
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
        return
    
    try:
        # Initialize the LLM
        llm = ChatOpenAI(model=model_name, api_key=os.getenv("OPENAI_API_KEY"))
        
        # Connect to the Google Drive MCP server
        mcp_client = MultiServerMCPClient(
            {
                "googledrivertools": {
                    "url": DRIVE_MCP_URL,
                    "transport": "sse",
                }
            }
        )
        
        await mcp_client.__aenter__()
        
        try:
            # Get tools from the MCP server
            mcp_tools = mcp_client.get_tools()
            logger.info(f"Loaded {len(mcp_tools)} tools from MCP servers")
            
            # Create a React agent with tools and system prompt
            agent = create_react_agent(
                llm,
                mcp_tools,
                prompt=GDRIVE_AGENT_PROMPT
            )
            
            # Create the user query
            user_message = f"""
            {query}
            """
            
            # Run the agent
            logger.info(f"Processing query: {query}")
            result = await agent.ainvoke({
                "messages": [
                    HumanMessage(content=user_message)
                ]
            })
            
            # Display the response
            ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
            if ai_messages:
                print("\n===== GOOGLE DRIVE ASSISTANT RESPONSE =====")
                print(ai_messages[-1].content)
            else:
                print("No response was generated")
                
        finally:
            # Clean up
            await mcp_client.__aexit__(None, None, None)
            
    except Exception as e:
        logger.error(f"Error running Google Drive agent: {str(e)}")
        print(f"Error: {str(e)}")

async def main():
    """Main function to run the Google Drive agent."""
    parser = argparse.ArgumentParser(description="Google Drive Assistant")
    parser.add_argument("query", nargs="?", help="Natural language query for Google Drive operations (required unless using --interactive)")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model to use")
    args = parser.parse_args()
    
    if args.interactive:
        print("\n===== Google Drive Assistant =====")
        print("Ask questions or give commands for Google Drive operations.")
        print("Examples:")
        print(" - \"Show me my recent files\"")
        print(" - \"Create a new document called 'Meeting Notes'\"")
        print(" - \"Upload the budget.xlsx file to my drive\"")
        print(" - \"Share my presentation with john@example.com\"")
        print(" - \"Create a new folder for project documents\"")
        print(" - \"Download my quarterly report PDF\"")
        print(" - \"Search for files containing 'project plan'\"")
        print("Type 'exit' or 'quit' to end the session.")
        
        while True:
            # Get query from user
            query = input("\nWhat would you like to do with Google Drive? ")
            
            # Check for exit command
            if query.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            # Skip empty queries
            if not query.strip():
                continue
                
            # Process the query
            await run_gdrive_agent(query, args.model)
    elif args.query:
        await run_gdrive_agent(args.query, args.model)
    else:
        print("Please provide a query or use --interactive mode")
        print("Example: python agent_client.py \"Show me my recent files\"")
        print("Example: python agent_client.py \"Create a new document called Meeting Notes\"")
        print("Example: python agent_client.py \"Upload budget.xlsx to my drive\"")
        print("Example: python agent_client.py \"Share my presentation with john@example.com\"")
        print("Example: python agent_client.py \"Search for files containing project plan\"")
        print("Example: python agent_client.py -i")

if __name__ == "__main__":
    asyncio.run(main())
