#!/usr/bin/env python
"""
Google Calendar MCP Server - Provides Google Calendar management and scheduling services via MCP protocol.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport
import uvicorn
import logging
import logging.config
from pathlib import Path
from datetime import datetime, timedelta

# Import configurations
try:
    from config import (
        LOGGING_CONFIG,
        MCP_HOST,
        CALENDAR_MCP_PORT,
        DEFAULT_TIMEZONE
    )
except ImportError:
    # Default configurations if not available
    LOGGING_CONFIG = {
        'version': 1,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'filename': 'gcalendar_mcp_server.log',
                'mode': 'a'
            }
        },
        'loggers': {
            'gcalendar_mcp_server': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False
            }
        }
    }
    MCP_HOST = "localhost"
    CALENDAR_MCP_PORT = 3007
    DEFAULT_TIMEZONE = "Asia/Kolkata"  # Default to Mumbai timezone

# Import helper
from calendar_helper import (
    calendar_helper, 
    ensure_authenticated
)

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('gcalendar_mcp_server')

# Create MCP server
mcp = FastMCP("GoogleCalendarTools")

# -------------------------------------------------------------------------
# List Calendars Tool
# -------------------------------------------------------------------------

class CalendarsRequest(BaseModel):
    pass

class CalendarsResponse(BaseModel):
    calendars: List[Dict[str, Any]]
    error: Optional[str] = None

@mcp.tool()
async def list_calendars(request: CalendarsRequest) -> CalendarsResponse:
    """
    List all calendars available to the authenticated user.
    
    Returns:
        An object containing the calendars and any error messages.
    """
    try:
        logger.info("Listing Google Calendars")
        
        # Use helper to get calendars
        result = calendar_helper.list_calendars()
        
        if result["error"]:
            logger.error(result["error"])
            return CalendarsResponse(
                calendars=[],
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved {len(result['calendars'])} calendars")
        return CalendarsResponse(
            calendars=result["calendars"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in list_calendars: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return CalendarsResponse(calendars=[], error=error_msg)

# -------------------------------------------------------------------------
# Get Calendar Tool
# -------------------------------------------------------------------------

class GetCalendarRequest(BaseModel):
    calendar_id: str = Field(description="ID of the calendar. Use 'primary' for primary calendar.")

class CalendarResponse(BaseModel):
    calendar: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def get_calendar(request: GetCalendarRequest) -> CalendarResponse:
    """
    Get details for a specific calendar.
    
    Args:
        request: An object containing the calendar ID.
        
    Returns:
        An object containing the calendar details and any error messages.
    """
    try:
        logger.info(f"Getting calendar details for: {request.calendar_id}")
        
        # Use helper to get calendar
        result = calendar_helper.get_calendar(
            calendar_id=request.calendar_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return CalendarResponse(
                calendar=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved calendar: {result['calendar'].get('summary')}")
        return CalendarResponse(
            calendar=result["calendar"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_calendar: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return CalendarResponse(calendar=None, error=error_msg)

# -------------------------------------------------------------------------
# Create Calendar Tool
# -------------------------------------------------------------------------

class CreateCalendarRequest(BaseModel):
    summary: str = Field(description="Name of the calendar")
    description: Optional[str] = Field(None, description="Description of the calendar")
    timezone: Optional[str] = Field(None, description="Timezone for the calendar")

@mcp.tool()
async def create_calendar(request: CreateCalendarRequest) -> CalendarResponse:
    """
    Create a new calendar.
    
    Args:
        request: An object containing calendar creation parameters.
        
    Returns:
        An object containing the created calendar details and any error messages.
    """
    try:
        logger.info(f"Creating calendar: {request.summary}")
        
        # Use helper to create calendar
        result = calendar_helper.create_calendar(
            summary=request.summary,
            description=request.description,
            timezone=request.timezone
        )
        
        if result["error"]:
            logger.error(result["error"])
            return CalendarResponse(
                calendar=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully created calendar: {result['calendar'].get('summary')}")
        return CalendarResponse(
            calendar=result["calendar"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in create_calendar: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return CalendarResponse(calendar=None, error=error_msg)

# -------------------------------------------------------------------------
# Delete Calendar Tool
# -------------------------------------------------------------------------

class DeleteCalendarRequest(BaseModel):
    calendar_id: str = Field(description="ID of the calendar to delete")

class DeleteCalendarResponse(BaseModel):
    success: bool
    error: Optional[str] = None

@mcp.tool()
async def delete_calendar(request: DeleteCalendarRequest) -> DeleteCalendarResponse:
    """
    Delete a calendar.
    
    Args:
        request: An object containing the calendar ID to delete.
        
    Returns:
        An object containing the success status and any error messages.
    """
    try:
        logger.info(f"Deleting calendar: {request.calendar_id}")
        
        # Use helper to delete calendar
        result = calendar_helper.delete_calendar(
            calendar_id=request.calendar_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DeleteCalendarResponse(
                success=False,
                error=result["error"]
            )
        
        logger.info(f"Successfully deleted calendar: {request.calendar_id}")
        return DeleteCalendarResponse(
            success=True,
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in delete_calendar: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DeleteCalendarResponse(success=False, error=error_msg)

# -------------------------------------------------------------------------
# List Events Tool
# -------------------------------------------------------------------------

class ListEventsRequest(BaseModel):
    calendar_id: Optional[str] = Field("primary", description="ID of the calendar. Use 'primary' for primary calendar.")
    time_min: Optional[str] = Field(None, description="Lower bound for event's start time in RFC3339 format")
    time_max: Optional[str] = Field(None, description="Upper bound for event's start time in RFC3339 format")
    max_results: Optional[int] = Field(10, description="Maximum number of events to return")
    q: Optional[str] = Field(None, description="Full text search query")

class EventsResponse(BaseModel):
    events: List[Dict[str, Any]]
    error: Optional[str] = None

@mcp.tool()
async def list_events(request: ListEventsRequest) -> EventsResponse:
    """
    List events in a calendar.
    
    Args:
        request: An object containing search parameters for events.
        
    Returns:
        An object containing the events and any error messages.
    """
    try:
        logger.info(f"Listing events from calendar: {request.calendar_id}")
        
        # Use helper to list events
        result = calendar_helper.list_events(
            calendar_id=request.calendar_id,
            time_min=request.time_min,
            time_max=request.time_max,
            max_results=request.max_results,
            q=request.q
        )
        
        if result["error"]:
            logger.error(result["error"])
            return EventsResponse(
                events=[],
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved {len(result['events'])} events")
        return EventsResponse(
            events=result["events"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in list_events: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return EventsResponse(events=[], error=error_msg)

# -------------------------------------------------------------------------
# Get Event Tool
# -------------------------------------------------------------------------

class GetEventRequest(BaseModel):
    calendar_id: str = Field(description="ID of the calendar. Use 'primary' for primary calendar.")
    event_id: str = Field(description="ID of the event to retrieve")

class EventResponse(BaseModel):
    event: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def get_event(request: GetEventRequest) -> EventResponse:
    """
    Get details for a specific event.
    
    Args:
        request: An object containing the calendar ID and event ID.
        
    Returns:
        An object containing the event details and any error messages.
    """
    try:
        logger.info(f"Getting event {request.event_id} from calendar {request.calendar_id}")
        
        # Use helper to get event
        result = calendar_helper.get_event(
            calendar_id=request.calendar_id,
            event_id=request.event_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return EventResponse(
                event=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved event: {result['event'].get('summary')}")
        return EventResponse(
            event=result["event"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_event: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return EventResponse(event=None, error=error_msg)

# -------------------------------------------------------------------------
# Create Event Tool
# -------------------------------------------------------------------------

class CreateEventRequest(BaseModel):
    calendar_id: Optional[str] = Field("primary", description="ID of the calendar. Use 'primary' for primary calendar.")
    summary: str = Field(description="Title of the event")
    location: Optional[str] = Field(None, description="Location of the event")
    description: Optional[str] = Field(None, description="Description of the event")
    start_time: Optional[str] = Field(None, description="Start time in RFC3339 format or readable format")
    end_time: Optional[str] = Field(None, description="End time in RFC3339 format or readable format")
    attendees: Optional[List[Dict[str, str]]] = Field(None, description="List of attendees [{'email': 'person@example.com'}, ...]")
    recurrence: Optional[List[str]] = Field(None, description="List of recurrence rules ['RRULE:FREQ=DAILY;COUNT=2', ...]")
    color_id: Optional[str] = Field(None, description="Color ID for the event")
    reminders: Optional[Dict[str, Any]] = Field(None, description="Reminder settings {'useDefault': False, 'overrides': [...]}")

@mcp.tool()
async def create_event(request: CreateEventRequest) -> EventResponse:
    """
    Create a new event in a calendar.
    
    Args:
        request: An object containing event creation parameters.
        
    Returns:
        An object containing the created event details and any error messages.
    """
    try:
        logger.info(f"Creating event '{request.summary}' in calendar {request.calendar_id}")
        
        # Use helper to create event
        result = calendar_helper.create_event(
            calendar_id=request.calendar_id,
            summary=request.summary,
            location=request.location,
            description=request.description,
            start_time=request.start_time,
            end_time=request.end_time,
            attendees=request.attendees,
            recurrence=request.recurrence,
            color_id=request.color_id,
            reminders=request.reminders
        )
        
        if result["error"]:
            logger.error(result["error"])
            return EventResponse(
                event=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully created event: {result['event'].get('summary')}")
        return EventResponse(
            event=result["event"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in create_event: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return EventResponse(event=None, error=error_msg)

# -------------------------------------------------------------------------
# Update Event Tool
# -------------------------------------------------------------------------

class UpdateEventRequest(BaseModel):
    calendar_id: str = Field(description="ID of the calendar. Use 'primary' for primary calendar.")
    event_id: str = Field(description="ID of the event to update")
    summary: Optional[str] = Field(None, description="Title of the event")
    location: Optional[str] = Field(None, description="Location of the event")
    description: Optional[str] = Field(None, description="Description of the event")
    start_time: Optional[str] = Field(None, description="Start time in RFC3339 format or readable format")
    end_time: Optional[str] = Field(None, description="End time in RFC3339 format or readable format")
    attendees: Optional[List[Dict[str, str]]] = Field(None, description="List of attendees [{'email': 'person@example.com'}, ...]")
    recurrence: Optional[List[str]] = Field(None, description="List of recurrence rules ['RRULE:FREQ=DAILY;COUNT=2', ...]")
    color_id: Optional[str] = Field(None, description="Color ID for the event")
    reminders: Optional[Dict[str, Any]] = Field(None, description="Reminder settings {'useDefault': False, 'overrides': [...]}")

@mcp.tool()
async def update_event(request: UpdateEventRequest) -> EventResponse:
    """
    Update an existing event in a calendar.
    
    Args:
        request: An object containing event update parameters.
        
    Returns:
        An object containing the updated event details and any error messages.
    """
    try:
        logger.info(f"Updating event {request.event_id} in calendar {request.calendar_id}")
        
        # Use helper to update event
        result = calendar_helper.update_event(
            calendar_id=request.calendar_id,
            event_id=request.event_id,
            summary=request.summary,
            location=request.location,
            description=request.description,
            start_time=request.start_time,
            end_time=request.end_time,
            attendees=request.attendees,
            recurrence=request.recurrence,
            color_id=request.color_id,
            reminders=request.reminders
        )
        
        if result["error"]:
            logger.error(result["error"])
            return EventResponse(
                event=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully updated event: {result['event'].get('summary')}")
        return EventResponse(
            event=result["event"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in update_event: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return EventResponse(event=None, error=error_msg)

# -------------------------------------------------------------------------
# Delete Event Tool
# -------------------------------------------------------------------------

class DeleteEventRequest(BaseModel):
    calendar_id: str = Field(description="ID of the calendar. Use 'primary' for primary calendar.")
    event_id: str = Field(description="ID of the event to delete")

class DeleteEventResponse(BaseModel):
    success: bool
    error: Optional[str] = None

@mcp.tool()
async def delete_event(request: DeleteEventRequest) -> DeleteEventResponse:
    """
    Delete an event from a calendar.
    
    Args:
        request: An object containing the calendar ID and event ID to delete.
        
    Returns:
        An object containing the success status and any error messages.
    """
    try:
        logger.info(f"Deleting event {request.event_id} from calendar {request.calendar_id}")
        
        # Use helper to delete event
        result = calendar_helper.delete_event(
            calendar_id=request.calendar_id,
            event_id=request.event_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DeleteEventResponse(
                success=False,
                error=result["error"]
            )
        
        logger.info(f"Successfully deleted event {request.event_id}")
        return DeleteEventResponse(
            success=True,
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in delete_event: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DeleteEventResponse(success=False, error=error_msg)

# -------------------------------------------------------------------------
# Free/Busy Tool
# -------------------------------------------------------------------------

class FreeBusyRequest(BaseModel):
    calendar_ids: List[str] = Field(description="List of calendar IDs to check availability")
    start_time: str = Field(description="Start time in RFC3339 format or readable format")
    end_time: str = Field(description="End time in RFC3339 format or readable format")
    timezone: Optional[str] = Field("UTC", description="Timezone for the query")

class FreeBusyResponse(BaseModel):
    calendars: Dict[str, Any]
    error: Optional[str] = None

@mcp.tool()
async def find_free_busy(request: FreeBusyRequest) -> FreeBusyResponse:
    """
    Check free/busy information for calendars in a specific time range.
    
    Args:
        request: An object containing calendars and time range parameters.
        
    Returns:
        An object containing free/busy information and any error messages.
    """
    try:
        logger.info(f"Checking free/busy for {len(request.calendar_ids)} calendars")
        
        # Use helper to get free/busy information
        result = calendar_helper.find_free_busy(
            calendar_ids=request.calendar_ids,
            start_time=request.start_time,
            end_time=request.end_time,
            timezone=request.timezone
        )
        
        if result["error"]:
            logger.error(result["error"])
            return FreeBusyResponse(
                calendars={},
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved free/busy information")
        return FreeBusyResponse(
            calendars=result["calendars"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in find_free_busy: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return FreeBusyResponse(calendars={}, error=error_msg)

# -------------------------------------------------------------------------
# Quick Add Event Tool
# -------------------------------------------------------------------------

class QuickAddEventRequest(BaseModel):
    calendar_id: Optional[str] = Field("primary", description="ID of the calendar. Use 'primary' for primary calendar.")
    text: str = Field(description="Text describing the event (e.g., 'Meeting tomorrow at 3pm')")

@mcp.tool()
async def quick_add_event(request: QuickAddEventRequest) -> EventResponse:
    """
    Quickly add an event using natural language processing.
    
    Args:
        request: An object containing the calendar ID and text describing the event.
        
    Returns:
        An object containing the created event details and any error messages.
    """
    try:
        logger.info(f"Quick adding event '{request.text}' to calendar {request.calendar_id}")
        
        # Use helper to quick add event
        result = calendar_helper.quick_add_event(
            calendar_id=request.calendar_id,
            text=request.text
        )
        
        if result["error"]:
            logger.error(result["error"])
            return EventResponse(
                event=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully quick-added event: {result['event'].get('summary')}")
        return EventResponse(
            event=result["event"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in quick_add_event: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return EventResponse(event=None, error=error_msg)

# -------------------------------------------------------------------------
# Authentication Tool
# -------------------------------------------------------------------------

class AuthenticationRequest(BaseModel):
    pass

class AuthenticationResponse(BaseModel):
    authenticated: bool
    message: str
    error: Optional[str] = None

@mcp.tool()
async def authenticate_calendar(request: AuthenticationRequest) -> AuthenticationResponse:
    """
    Authenticate with Google Calendar API.
    
    Returns:
        An object containing authentication status and any error messages.
    """
    try:
        logger.info("Authenticating with Google Calendar")
        
        # Ensure authentication
        auth_result = ensure_authenticated()
        
        if not auth_result["success"]:
            logger.error(auth_result["error"])
            return AuthenticationResponse(
                authenticated=False,
                message="Authentication failed",
                error=auth_result["error"]
            )
        
        logger.info("Successfully authenticated with Google Calendar")
        return AuthenticationResponse(
            authenticated=True,
            message="Successfully authenticated with Google Calendar",
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in authenticate_calendar: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return AuthenticationResponse(
            authenticated=False, 
            message="Authentication failed due to an error",
            error=error_msg
        )

# -------------------------------------------------------------------------
# Server Setup
# -------------------------------------------------------------------------

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

    # Get MCP server instance from FastMCP
    mcp_server = mcp._mcp_server

    parser = argparse.ArgumentParser(description="Google Calendar MCP Server")
    parser.add_argument("--port", type=int, default=CALENDAR_MCP_PORT, help="Port for server")
    parser.add_argument("--host", type=str, default=MCP_HOST, help="Host for server")
    parser.add_argument("--skip-auth-check", action="store_true", help="Skip authentication check before starting server")
    parser.add_argument("--timezone", type=str, default=DEFAULT_TIMEZONE, help="Timezone for calendar operations")
    
    args = parser.parse_args()
    
    # Check authentication before starting the server
    if not args.skip_auth_check:
        logger.info("Checking Google Calendar API authentication before starting server")
        
        auth_result = ensure_authenticated()
        
        if auth_result["success"]:
            logger.info("Authentication successful")
        else:
            logger.error(f"Authentication failed: {auth_result['error']}")
            
            # Print a user-friendly message
            print("\n" + "="*80)
            print(" AUTHENTICATION ERROR ".center(80, "="))
            print("="*80)
            print(f"\nFailed to authenticate with Google Calendar API: {auth_result['error']}")
            print("\nThe server will still start, but Calendar-related operations may fail.")
            print("You can try accessing the server and authenticating through API requests.")
            print("\nTo bypass this check next time, use --skip-auth-check\n")
    
    logger.info(f"Starting Google Calendar MCP Server on {args.host}:{args.port}")
    logger.info(f"Using timezone: {args.timezone} (Mumbai/India)")
    
    # Print server info
    print("\n" + "="*80)
    print(" GOOGLE CALENDAR MCP SERVER ".center(80, "="))
    print("="*80)
    print(f"Server URL: http://{args.host}:{args.port}/sse")
    print(f"Timezone: {args.timezone} (Mumbai/India)")
    print("="*80 + "\n")
    
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