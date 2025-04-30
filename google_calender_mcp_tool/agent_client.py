#!/usr/bin/env python3
"""
Google Calendar MCP Agent Client - Simple client for Google Calendar operations through MCP
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
    CALENDAR_MCP_URL,
    DEFAULT_TIMEZONE
)

# LangChain MCP adapter imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('gcalendar_mcp_agent')

# Google Calendar Assistant Agent Prompt
GCALENDAR_AGENT_PROMPT = """
You are a helpful Google Calendar assistant with the following capabilities:

1. CALENDAR MANAGEMENT:
   - GoogleCalendarTools.list_calendars: List all calendars available to the user
   - GoogleCalendarTools.get_calendar: Get details for a specific calendar
   - GoogleCalendarTools.create_calendar: Create a new calendar
   - GoogleCalendarTools.delete_calendar: Delete a calendar

2. EVENT MANAGEMENT:
   - GoogleCalendarTools.list_events: List events in a calendar
   - GoogleCalendarTools.get_event: Get details for a specific event
   - GoogleCalendarTools.create_event: Create a new event in a calendar
   - GoogleCalendarTools.update_event: Update an existing event
   - GoogleCalendarTools.delete_event: Delete an event from a calendar

3. SCHEDULING:
   - GoogleCalendarTools.quick_add_event: Quickly add an event using natural language
   - GoogleCalendarTools.find_free_busy: Check free/busy information for calendars

4. AUTHENTICATION:
   - GoogleCalendarTools.authenticate_calendar: Authenticate with Google Calendar

IMPORTANT: The user is in Mumbai, India (Asia/Kolkata timezone, UTC+5:30). All times should be interpreted and displayed in this timezone.

Analyze the user's query to determine which tool to use:

- For VIEWING CALENDARS: Use list_calendars to see all available calendars
  Examples: "Show me my calendars", "List all my calendars", "What calendars do I have?"

- For CALENDAR DETAILS: Use get_calendar to get information about a specific calendar
  Examples: "Show details for my work calendar", "Get information about my primary calendar"

- For CALENDAR CREATION/DELETION: Use create_calendar or delete_calendar
  Examples: "Create a new calendar called 'Vacation'", "Delete my 'Old Projects' calendar"

- For VIEWING EVENTS: Use list_events to see scheduled events
  Examples: "Show me my events for today", "List all meetings this week", "What's on my calendar for tomorrow?"
  Examples: "Show events in my Work calendar for next week", "Find all events containing 'project review'"

- For EVENT DETAILS: Use get_event to get information about a specific event
  Examples: "Show details for my meeting with John", "Tell me about my 3pm appointment tomorrow"

- For EVENT CREATION: Use create_event to add events
  Examples: "Schedule a meeting with marketing team on Friday at 2pm", "Add a dentist appointment on June 5th at 10am"
  Examples: "Create a recurring team meeting every Monday at 9am", "Schedule a video call with client tomorrow at 3pm"

- For EVENT UPDATES: Use update_event to modify existing events
  Examples: "Change my 2pm meeting to 3pm", "Update tomorrow's lunch location to Cafe Central"
  Examples: "Add John and Mary as attendees to my project review", "Change the color of my workout events to green"

- For EVENT DELETION: Use delete_event to remove events
  Examples: "Cancel my dentist appointment", "Delete tomorrow's team lunch", "Remove the conference call on Friday"

- For QUICK EVENT CREATION: Use quick_add_event for simple natural language event creation
  Examples: "Add lunch with John tomorrow at noon", "Schedule team meeting on Friday at 3pm"

- For AVAILABILITY CHECKING: Use find_free_busy to check for available time slots
  Examples: "When am I free tomorrow?", "Check if I'm busy next Friday afternoon"
  Examples: "Find available time slots for a meeting with marketing team next week"

Always authenticate first if the user needs to access their calendar data.
For calendar operations, use the primary calendar by default unless the user specifies a different one.
For date-time values, use the Mumbai, India timezone (Asia/Kolkata, UTC+5:30) as the default timezone.

When working with events:
1. For retrieving events, narrow down by time range, search terms, or calendar ID
2. For creating events, collect essential information (summary, start/end times, attendees)
3. For updating events, first identify the event, then apply the changes
4. For checking availability, specify the time range and required calendars

Always respond in a clear, concise, and helpful manner. Ask for clarification if
the user's request is ambiguous or lacks necessary details.
"""

async def run_gcalendar_agent(query: str, model_name: str = DEFAULT_MODEL) -> None:
    """
    Run the Google Calendar Agent with the provided query
    
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
        
        # Connect to the Google Calendar MCP server
        mcp_client = MultiServerMCPClient(
            {
                "googlecalendartools": {
                    "url": CALENDAR_MCP_URL,
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
                prompt=GCALENDAR_AGENT_PROMPT
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
                print("\n===== GOOGLE CALENDAR ASSISTANT RESPONSE =====")
                print(ai_messages[-1].content)
            else:
                print("No response was generated")
                
        finally:
            # Clean up
            await mcp_client.__aexit__(None, None, None)
            
    except Exception as e:
        logger.error(f"Error running Google Calendar agent: {str(e)}")
        print(f"Error: {str(e)}")

async def main():
    """Main function to run the Google Calendar agent."""
    parser = argparse.ArgumentParser(description="Google Calendar Assistant")
    parser.add_argument("query", nargs="?", help="Natural language query for Google Calendar operations (required unless using --interactive)")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model to use")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help="Timezone for calendar operations (default: Mumbai, India)")
    args = parser.parse_args()
    
    if args.interactive:
        print("\n===== Google Calendar Assistant =====")
        print(f"Timezone: {args.timezone} (Mumbai, India)")
        print("Ask questions or give commands for Google Calendar operations.")
        print("Examples:")
        print(" - \"Show me my events for today\"")
        print(" - \"Schedule a meeting tomorrow at 2pm\"")
        print(" - \"When am I free next week?\"")
        print(" - \"Create a new calendar for personal projects\"")
        print(" - \"Add a dentist appointment on Friday at 10am\"")
        print(" - \"List all my calendars\"")
        print(" - \"Delete the event called 'Old Meeting'\"")
        print("Type 'exit' or 'quit' to end the session.")
        
        while True:
            # Get query from user
            query = input("\nWhat would you like to do with Google Calendar? ")
            
            # Check for exit command
            if query.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            # Skip empty queries
            if not query.strip():
                continue
                
            # Process the query
            await run_gcalendar_agent(query, args.model)
    elif args.query:
        await run_gcalendar_agent(args.query, args.model)
    else:
        print("Please provide a query or use --interactive mode")
        print(f"Using timezone: {args.timezone} (Mumbai, India)")
        print("Example: python agent_client.py \"Show me my events for today\"")
        print("Example: python agent_client.py \"Schedule a meeting tomorrow at 2pm\"")
        print("Example: python agent_client.py \"Create a new calendar for work\"")
        print("Example: python agent_client.py \"When am I free next Monday?\"")
        print("Example: python agent_client.py \"Add a doctor appointment Friday at 3pm\"")
        print("Example: python agent_client.py -i")

if __name__ == "__main__":
    asyncio.run(main()) 