#!/usr/bin/env python3
"""
Gmail MCP Agent Client - Simple client for accessing Gmail API through MCP
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
    GMAIL_MCP_URL,
    DEFAULT_MODEL,
    DEFAULT_MAX_RESULTS,
    SYSTEM_PROMPTS,
    ERROR_MESSAGES
)

# LangChain MCP adapter imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('gmail_mcp_agent')

# Gmail Assistant Agent Prompt
GMAIL_AGENT_PROMPT = """
You are a helpful Gmail assistant with the following capabilities:

1. MESSAGE MANAGEMENT:
   - GmailTools.list_gmail_messages: Search and analyze Gmail messages
   - GmailTools.get_gmail_profile: Get account information (email, message counts)
   - GmailTools.setup_gmail_watch: Configure push notifications
   - GmailTools.send_gmail_message: Send a new email directly
   - GmailTools.modify_gmail_message: Change labels on messages (mark read/unread, important)

2. THREAD MANAGEMENT:
   - GmailTools.list_gmail_threads: List email conversation threads
   - GmailTools.get_gmail_thread: Retrieve conversation thread with message metadata

3. LABEL MANAGEMENT:
   - GmailTools.list_gmail_labels: List all email labels (system and custom)
   - GmailTools.create_gmail_label: Create a new custom label
   - GmailTools.update_gmail_label: Update an existing label's properties

4. FILTER MANAGEMENT:
   - GmailTools.list_gmail_filters: List all email filters
   - GmailTools.create_gmail_filter: Create a new filter to process incoming emails

5. DRAFT MANAGEMENT:
   - GmailTools.create_gmail_draft: Create a new draft email
   - GmailTools.delete_gmail_draft: Delete a specific draft
   - GmailTools.get_gmail_draft: Retrieve details of a specific draft
   - GmailTools.list_gmail_drafts: List all drafts in the mailbox
   - GmailTools.send_gmail_draft: Send an existing draft
   - GmailTools.update_gmail_draft: Update content of an existing draft

6. HISTORY TRACKING:
   - GmailTools.load_saved_history_id: Load previously saved history ID
   - GmailTools.get_gmail_history: Track changes in mailbox since a specific point in time

For email searches, use Gmail search syntax:
- from:name, to:name, subject:word
- has:attachment, is:unread, is:starred
- after:YYYY/MM/DD, before:YYYY/MM/DD

Analyze the user's query to determine which tool to use:

- For ACCOUNT INFO: Use get_gmail_profile to show email address and counts
  Examples: "What's my email?", "Show my account details"

- For MESSAGE SEARCH: Use list_gmail_messages with appropriate search syntax
  Examples: "Find emails from John", "Show my unread messages"

- For THREAD SEARCH: Use list_gmail_threads to find conversations
  Examples: "Find conversation threads with Sarah", "Show email threads about project X"
  Examples: "Show me all conversation threads from last week"

- For CONVERSATION RETRIEVAL: Use get_gmail_thread to show full conversation history
  Examples: "Show me the full conversation with thread ID abc123"
  Examples: "Get the complete email thread about the budget proposal"

- For LABEL MANAGEMENT: Use label tools to organize emails
  Examples: "List all my Gmail labels", "Create a new label called 'Urgent'"
  Examples: "Update the color of my 'Work' label to red"

- For FILTER MANAGEMENT: Use filter tools to automate email processing
  Examples: "Show all my email filters", "Create a filter for messages from boss@company.com"
  Examples: "Set up a filter to apply the 'Urgent' label to emails with 'ASAP' in the subject"

- For NOTIFICATION SETUP: Explain requirements for setup_gmail_watch
  Examples: "How do I set up notifications?", "Watch my inbox"

- For SENDING EMAILS: Use send_gmail_message for direct sending
  Examples: "Send an email to john@example.com", "Email my boss about the project"
  Examples: "Write to support@company.com about my order"

- For MODIFYING MESSAGES: Use modify_gmail_message to change labels/status
  Examples: "Mark the email from John as read", "Flag the budget email as important"
  Examples: "Mark all emails from HR as unread", "Remove importance from the sales emails"

- For DRAFT CREATION: Use create_gmail_draft with user-supplied details
  Examples: "Create a draft to boss@company.com", "Draft an email about meeting"

- For DRAFT LISTING: Use list_gmail_drafts to show all drafts
  Examples: "Show my drafts", "List all draft emails"

- For DRAFT OPERATIONS: Use appropriate draft tools based on context
  Examples: "Get draft with ID xyz", "Delete draft abc", "Send draft 123"

- For HISTORY TRACKING: Use history tracking tools to monitor mailbox changes
  Examples: "What's changed in my inbox?", "Show recent mailbox activity"
  Examples: "Track new messages since last check", "Has anything changed in my inbox?"

The key difference between messages and threads:
- Messages are individual emails
- Threads are conversations that group related messages together
When the user wants to see a complete conversation, use thread operations.

Note that thread retrieval shows message metadata (sender, recipient, subject, date, snippet)
rather than full message content due to permission constraints.

For label creation, you need:
- Label name (required)
- Text color and background color (optional, hex format like '#000000')

For filter creation, you need:
- Criteria (at least one of: from, to, subject, query, has_attachment)
- Action (at least one of: add_label_ids, remove_label_ids, forward)

When using history tracking:
1. First use load_saved_history_id to get the previous history ID checkpoint
2. Then use get_gmail_history with that ID to see what's changed
3. If no history ID exists, inform the user this is the first check and establish baseline

When sending emails or creating drafts, ask for necessary information if not provided:
- Recipient email address (to)
- Subject line
- Message content

For message modification tasks:
1. If the user doesn't specify which message to modify, list recent messages first
2. Common label operations include: mark as read (remove UNREAD), mark as unread (add UNREAD),
   mark as important (add IMPORTANT), remove importance (remove IMPORTANT)

Always respond in a clear, concise, and helpful manner. For operations that
require a message, thread, or draft ID, help the user find the ID first if they don't provide one.
"""

async def run_gmail_agent(query: str, max_results: int = DEFAULT_MAX_RESULTS, model_name: str = DEFAULT_MODEL) -> None:
    """
    Run the Gmail Agent with the provided query
    
    Args:
        query: Natural language query
        max_results: Maximum number of results for message queries
        model_name: LLM model to use
    """
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
        return
    
    try:
        # Initialize the LLM
        llm = ChatOpenAI(model=model_name, api_key=os.getenv("OPENAI_API_KEY"))
        
        # Connect to the Gmail MCP server
        mcp_client = MultiServerMCPClient(
            {
                "gmailtools": {
                    "url": GMAIL_MCP_URL,
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
                prompt=GMAIL_AGENT_PROMPT
            )
            
            # Create the user query
            user_message = f"""
            {query}
            
            For message or draft searches, use a maximum of {max_results} results.
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
                print("\n===== GMAIL ASSISTANT RESPONSE =====")
                print(ai_messages[-1].content)
            else:
                print("No response was generated")
                
        finally:
            # Clean up
            await mcp_client.__aexit__(None, None, None)
            
    except Exception as e:
        logger.error(f"Error running Gmail agent: {str(e)}")
        print(f"Error: {str(e)}")

async def main():
    """Main function to run the Gmail agent."""
    parser = argparse.ArgumentParser(description="Gmail Assistant")
    parser.add_argument("query", nargs="?", help="Natural language query about Gmail (required unless using --interactive)")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("-m", "--max-results", type=int, default=DEFAULT_MAX_RESULTS, help="Maximum number of messages to return")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model to use")
    args = parser.parse_args()
    
    if args.interactive:
        print("\n===== Gmail Assistant =====")
        print("Ask questions about your emails, drafts, account information, or notification setup.")
        print("Examples:")
        print(" - \"Show me my recent important emails\"")
        print(" - \"Find conversation threads about the quarterly report\"")
        print(" - \"List all my Gmail labels\"")
        print(" - \"Create a new label called 'Project X' with blue background\"")
        print(" - \"Show my email filters\"")
        print(" - \"Tell me about my Gmail account\"")
        print(" - \"Send an email to venkatsai.vavilashetty@indexnine.com about the project status\"")
        print(" - \"Mark the email from HR as important\"")
        print(" - \"Create a draft email to venkatsai.vavilashetty@indexnine.com about the meeting\"")
        print(" - \"List my draft emails\"")
        print(" - \"Send draft with ID r12345\"")
        print(" - \"What's changed in my inbox since last check?\"")
        print(" - \"Track recent activity in my mailbox\"")
        print("Type 'exit' or 'quit' to end the session.")
        
        while True:
            # Get query from user
            query = input("\nWhat would you like to do? ")
            
            # Check for exit command
            if query.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            # Skip empty queries
            if not query.strip():
                continue
                
            # Process the query
            await run_gmail_agent(query, args.max_results, args.model)
    elif args.query:
        await run_gmail_agent(args.query, args.max_results, args.model)
    else:
        print("Please provide a query or use --interactive mode")
        print("Example: python agent_client.py \"Show me my recent important emails\"")
        print("Example: python agent_client.py \"Get the conversation thread with John about the project\"")
        print("Example: python agent_client.py \"List all my Gmail labels\"")
        print("Example: python agent_client.py \"Create a filter for emails from boss@company.com\"")
        print("Example: python agent_client.py \"Send an email to support@example.com about my order\"")
        print("Example: python agent_client.py \"Mark emails from boss@company.com as important\"")
        print("Example: python agent_client.py \"Create a draft email to support@example.com\"")
        print("Example: python agent_client.py \"List all my drafts\"")
        print("Example: python agent_client.py \"What's changed in my inbox since last check?\"")
        print("Example: python agent_client.py -i")

if __name__ == "__main__":
    asyncio.run(main())
