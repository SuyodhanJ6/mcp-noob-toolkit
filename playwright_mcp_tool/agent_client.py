#!/usr/bin/env python3
"""
Playwright MCP Agent Client - Simple client for automation using Playwright through MCP
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
    PLAYWRIGHT_MCP_URL
)

# LangChain MCP adapter imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('playwright_mcp_agent')

# Playwright Assistant Agent Prompt
PLAYWRIGHT_AGENT_PROMPT = """
You are a helpful Playwright automation assistant with the following capabilities:

1. BROWSER AUTOMATION:
   - PlaywrightTools.launch_browser: Launch a new browser (chromium, firefox, webkit)
   - PlaywrightTools.navigate: Navigate to a specific URL
   - PlaywrightTools.screenshot: Take a screenshot of the current page
   - PlaywrightTools.close_browser: Close the browser

2. PAGE INTERACTION:
   - PlaywrightTools.click: Click on an element identified by a selector
   - PlaywrightTools.fill: Fill a form field with text
   - PlaywrightTools.select: Select an option from a dropdown
   - PlaywrightTools.check: Check/uncheck a checkbox
   - PlaywrightTools.press: Press a keyboard key

3. PAGE ANALYSIS:
   - PlaywrightTools.get_text: Get text content of an element
   - PlaywrightTools.get_attribute: Get attribute value of an element
   - PlaywrightTools.count_elements: Count elements matching a selector
   - PlaywrightTools.is_visible: Check if an element is visible
   - PlaywrightTools.wait_for_selector: Wait for an element to appear

4. DATA EXTRACTION:
   - PlaywrightTools.extract_table: Extract data from an HTML table
   - PlaywrightTools.get_page_title: Get the title of the current page
   - PlaywrightTools.get_page_url: Get the URL of the current page
   - PlaywrightTools.get_page_content: Get the HTML content of the page

5. ADVANCED INTERACTIONS:
   - PlaywrightTools.hover: Hover over an element
   - PlaywrightTools.drag_and_drop: Drag and drop elements
   - PlaywrightTools.upload_file: Upload a file to a form
   - PlaywrightTools.execute_javascript: Run JavaScript code on the page

Analyze the user's query to determine which tool to use:

- For BROWSER CONTROL: Use launch_browser to start automation and close_browser when finished
  Examples: "Open Chrome and go to Google", "Start Firefox and visit facebook.com"

- For NAVIGATION: Use navigate to visit websites
  Examples: "Go to github.com", "Navigate to twitter.com"

- For CLICKING ELEMENTS: Use click with appropriate selectors
  Examples: "Click the login button", "Click on the 'Submit' button"

- For FORM FILLING: Use fill to input text into forms
  Examples: "Type 'test@example.com' in the email field", "Fill the search box with 'Playwright'"

- For EXTRACTING DATA: Use appropriate extraction tools
  Examples: "Get the text of the main heading", "Extract data from the product table"
  Examples: "Get the title of the current page", "Check if the 'Login' button is visible"

- For TAKING SCREENSHOTS: Use screenshot to capture the current state
  Examples: "Take a screenshot of the page", "Capture a screenshot of the login form"

- For ADVANCED INTERACTIONS: Use specialized interaction tools
  Examples: "Hover over the dropdown menu", "Upload resume.pdf to the file input"
  Examples: "Drag the item to the shopping cart", "Execute JavaScript to scroll to bottom"

When interacting with elements, you'll need to use CSS selectors or XPath. Common examples:
- "#login-button" (ID selector)
- ".search-box" (Class selector)
- "button[type='submit']" (Attribute selector)
- "//button[contains(text(), 'Login')]" (XPath selector)

For complex automation tasks, break them down into sequential steps:
1. Launch the browser
2. Navigate to the target website
3. Interact with elements (click, fill, etc.)
4. Extract data or verify conditions
5. Take screenshots if needed
6. Close the browser when finished

Always respond in a clear, concise, and helpful manner. Ask for clarification if
the user's request is ambiguous or lacks necessary details.
"""

async def run_playwright_agent(query: str, model_name: str = DEFAULT_MODEL) -> None:
    """
    Run the Playwright Agent with the provided query
    
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
        
        # Connect to the Playwright MCP server
        mcp_client = MultiServerMCPClient(
            {
                "playwrighttools": {
                    "url": PLAYWRIGHT_MCP_URL,
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
                prompt=PLAYWRIGHT_AGENT_PROMPT
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
                print("\n===== PLAYWRIGHT ASSISTANT RESPONSE =====")
                print(ai_messages[-1].content)
            else:
                print("No response was generated")
                
        finally:
            # Clean up
            await mcp_client.__aexit__(None, None, None)
            
    except Exception as e:
        logger.error(f"Error running Playwright agent: {str(e)}")
        print(f"Error: {str(e)}")

async def main():
    """Main function to run the Playwright agent."""
    parser = argparse.ArgumentParser(description="Playwright Automation Assistant")
    parser.add_argument("query", nargs="?", help="Natural language query for Playwright automation (required unless using --interactive)")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model to use")
    args = parser.parse_args()
    
    if args.interactive:
        print("\n===== Playwright Automation Assistant =====")
        print("Ask questions or give commands for browser automation tasks.")
        print("Examples:")
        print(" - \"Open Chrome and go to Google\"")
        print(" - \"Navigate to github.com and search for 'playwright'\"")
        print(" - \"Fill the login form with username 'test' and password 'pass123'\"")
        print(" - \"Click the 'Submit' button\"")
        print(" - \"Take a screenshot of the current page\"")
        print(" - \"Extract text from the main heading\"")
        print(" - \"Get data from the products table\"")
        print(" - \"Check if the error message is visible\"")
        print("Type 'exit' or 'quit' to end the session.")
        
        while True:
            # Get query from user
            query = input("\nWhat would you like to automate? ")
            
            # Check for exit command
            if query.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            # Skip empty queries
            if not query.strip():
                continue
                
            # Process the query
            await run_playwright_agent(query, args.model)
    elif args.query:
        await run_playwright_agent(args.query, args.model)
    else:
        print("Please provide a query or use --interactive mode")
        print("Example: python agent_client.py \"Open Chrome and go to Google\"")
        print("Example: python agent_client.py \"Navigate to github.com and search for playwright\"")
        print("Example: python agent_client.py \"Fill the login form and click submit\"")
        print("Example: python agent_client.py \"Extract product information from amazon.com\"")
        print("Example: python agent_client.py \"Take a screenshot of the news section on cnn.com\"")
        print("Example: python agent_client.py -i")

if __name__ == "__main__":
    asyncio.run(main())
