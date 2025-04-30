#!/usr/bin/env python
"""
Helper functions for Google Calendar MCP tools
"""

import os
import io
import logging
from typing import Optional, Dict, Any, List, BinaryIO
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request as GoogleRequest
from datetime import datetime, timedelta
from dateutil.parser import parse
from dotenv import load_dotenv
from config import CALENDAR_SCOPES, TOKEN_PATH, CREDENTIALS_PATH, DEFAULT_TIMEZONE

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger('gcalendar_helper')

class GoogleCalendarHelper:
    """Helper class for Google Calendar operations"""
    
    def __init__(self, scopes: List[str], token_path: Path, credentials_path: Path):
        """Initialize Google Calendar helper.
        
        Args:
            scopes: List of Google Calendar API scopes
            token_path: Path to token.json
            credentials_path: Path to credentials.json
        """
        self.scopes = scopes
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.service = None
    
    def authenticate(self) -> bool:
        """Authenticate with Google Calendar API.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            creds = None
            # Load existing credentials if available
            if self.token_path.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)
                    logger.info("Using existing credentials from token file")
                except Exception as e:
                    logger.error(f"Error loading credentials: {e}")
                    return False

            # Handle credential refresh or new authentication
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        logger.info("Refreshing expired credentials")
                        creds.refresh(GoogleRequest())
                    except Exception as e:
                        logger.error(f"Error refreshing credentials: {e}")
                        # If refresh fails, we'll need to re-authenticate
                        creds = None
                
                # If still no valid credentials, start new authentication flow
                if not creds or not creds.valid:
                    try:
                        logger.info("No valid credentials found. Starting new authentication flow.")
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(self.credentials_path), self.scopes)
                        
                        # Print clear instructions for the user
                        print("\n" + "="*80)
                        print(" GOOGLE CALENDAR AUTHENTICATION REQUIRED ".center(80, "="))
                        print("="*80)
                        print("\nThis application needs to access your Google Calendar account.")
                        print("1. A browser window will open shortly.")
                        print("2. Select your Google account and grant the requested permissions.")
                        print("3. After authorization, you'll be redirected to a local page.")
                        print("\nIf no browser opens automatically, use the URL that will be displayed.\n")
                        
                        # Add access_type='offline' to get a refresh token
                        creds = flow.run_local_server(
                            port=8080, 
                            access_type='offline',
                            prompt='consent',  # Force prompt to ensure refresh token is provided
                            success_message="Authentication complete! You can close this window and return to the application."
                        )
                        
                        print("\n" + "="*80)
                        print(" AUTHENTICATION SUCCESSFUL ".center(80, "="))
                        print("="*80 + "\n")
                        
                    except Exception as e:
                        logger.error(f"Error in OAuth flow: {e}")
                        return False

                # Save credentials
                try:
                    logger.info("Saving new credentials to token file")
                    with open(self.token_path, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logger.error(f"Error saving credentials: {e}")
                    return False

            # Store credentials for use by other services
            self.credentials = creds
            
            # Build Google Calendar service
            self.service = build('calendar', 'v3', credentials=creds)
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def list_calendars(self) -> Dict[str, Any]:
        """List all calendars available to the authenticated user.
        
        Returns:
            Dict containing calendars and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "calendars": [],
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # Get calendars list
            response = self.service.calendarList().list().execute()
            calendars = response.get('items', [])
            
            if not calendars:
                return {
                    "calendars": [],
                    "error": "No calendars found for this user"
                }
            
            logger.info(f"Successfully retrieved {len(calendars)} calendars")
            return {
                "calendars": calendars,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error listing calendars: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "calendars": [],
                "error": error_msg
            }
    
    def get_calendar(self, calendar_id: str) -> Dict[str, Any]:
        """Get calendar details by ID.
        
        Args:
            calendar_id: ID of the calendar (use 'primary' for primary calendar)
            
        Returns:
            Dict containing calendar details and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "calendar": None,
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # Get calendar by ID
            calendar = self.service.calendars().get(calendarId=calendar_id).execute()
            
            logger.info(f"Successfully retrieved calendar: {calendar.get('summary')}")
            return {
                "calendar": calendar,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error getting calendar {calendar_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "calendar": None,
                "error": error_msg
            }
    
    def create_calendar(self, summary: str, description: str = None, 
                        timezone: str = DEFAULT_TIMEZONE) -> Dict[str, Any]:
        """Create a new calendar.
        
        Args:
            summary: Name of the calendar
            description: Description of the calendar
            timezone: Timezone for the calendar
            
        Returns:
            Dict containing calendar details and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "calendar": None,
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # Create calendar body
            calendar_body = {
                'summary': summary
            }
            
            if description:
                calendar_body['description'] = description
                
            if timezone:
                calendar_body['timeZone'] = timezone
            
            # Create the calendar
            created_calendar = self.service.calendars().insert(body=calendar_body).execute()
            
            logger.info(f"Successfully created calendar: {created_calendar.get('summary')}")
            return {
                "calendar": created_calendar,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error creating calendar {summary}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "calendar": None,
                "error": error_msg
            }
    
    def delete_calendar(self, calendar_id: str) -> Dict[str, Any]:
        """Delete a calendar.
        
        Args:
            calendar_id: ID of the calendar to delete
            
        Returns:
            Dict containing success status and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "success": False,
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # Cannot delete primary calendar
            if calendar_id.lower() == 'primary':
                return {
                    "success": False,
                    "error": "Cannot delete primary calendar"
                }
            
            # Delete the calendar
            self.service.calendars().delete(calendarId=calendar_id).execute()
            
            logger.info(f"Successfully deleted calendar: {calendar_id}")
            return {
                "success": True,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error deleting calendar {calendar_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
    
    def list_events(self, calendar_id: str = 'primary', 
                    time_min: str = None, time_max: str = None, 
                    max_results: int = 10, q: str = None) -> Dict[str, Any]:
        """List events in a calendar.
        
        Args:
            calendar_id: ID of the calendar (use 'primary' for primary calendar)
            time_min: Lower bound for event's start time
            time_max: Upper bound for event's start time
            max_results: Maximum number of events to return
            q: Full text search query
            
        Returns:
            Dict containing events and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "events": [],
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # Set default time range if not provided
            now = datetime.utcnow()
            if not time_min:
                time_min = now.isoformat() + 'Z'  # 'Z' indicates UTC time
            if not time_max:
                time_max = (now + timedelta(days=30)).isoformat() + 'Z'
            
            # Prepare parameters
            params = {
                'calendarId': calendar_id,
                'timeMin': time_min,
                'timeMax': time_max,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            if q:
                params['q'] = q
            
            # Get events
            events_result = self.service.events().list(**params).execute()
            events = events_result.get('items', [])
            
            if not events:
                return {
                    "events": [],
                    "error": f"No events found in calendar {calendar_id} for the specified time range"
                }
            
            logger.info(f"Successfully retrieved {len(events)} events")
            return {
                "events": events,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error listing events in calendar {calendar_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "events": [],
                "error": error_msg
            }
    
    def get_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        """Get an event by ID.
        
        Args:
            calendar_id: ID of the calendar (use 'primary' for primary calendar)
            event_id: ID of the event
            
        Returns:
            Dict containing event details and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "event": None,
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # Get event by ID
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Successfully retrieved event: {event.get('summary')}")
            return {
                "event": event,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error getting event {event_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "event": None,
                "error": error_msg
            }
    
    def create_event(self, calendar_id: str = 'primary', summary: str = None, 
                     location: str = None, description: str = None,
                     start_time: str = None, end_time: str = None, 
                     attendees: List[Dict[str, str]] = None,
                     recurrence: List[str] = None,
                     color_id: str = None,
                     reminders: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new event.
        
        Args:
            calendar_id: ID of the calendar (use 'primary' for primary calendar)
            summary: Title of the event
            location: Location of the event
            description: Description of the event
            start_time: Start time in RFC3339 format or datetime
            end_time: End time in RFC3339 format or datetime
            attendees: List of attendees [{'email': 'person@example.com'}, ...]
            recurrence: List of recurrence rules ['RRULE:FREQ=DAILY;COUNT=2', ...]
            color_id: Color ID for the event
            reminders: Reminder settings {'useDefault': False, 'overrides': [...]}
            
        Returns:
            Dict containing created event and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "event": None,
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # Set default times if not provided
            now = datetime.utcnow()
            
            # Handle different time formats
            start_datetime = self._parse_time(start_time) if start_time else now
            end_datetime = self._parse_time(end_time) if end_time else (start_datetime + timedelta(hours=1))
            
            # Create event body
            event_body = {
                'summary': summary or 'New Event',
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': DEFAULT_TIMEZONE,
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': DEFAULT_TIMEZONE,
                },
            }
            
            if location:
                event_body['location'] = location
                
            if description:
                event_body['description'] = description
                
            if attendees:
                event_body['attendees'] = attendees
                
            if recurrence:
                event_body['recurrence'] = recurrence
                
            if color_id:
                event_body['colorId'] = color_id
                
            if reminders:
                event_body['reminders'] = reminders
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            logger.info(f"Successfully created event: {created_event.get('summary')}")
            return {
                "event": created_event,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error creating event: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "event": None,
                "error": error_msg
            }
    
    def update_event(self, calendar_id: str, event_id: str, 
                     summary: str = None, location: str = None, 
                     description: str = None, start_time: str = None, 
                     end_time: str = None, attendees: List[Dict[str, str]] = None,
                     recurrence: List[str] = None, color_id: str = None,
                     reminders: Dict[str, Any] = None) -> Dict[str, Any]:
        """Update an existing event.
        
        Args:
            calendar_id: ID of the calendar (use 'primary' for primary calendar)
            event_id: ID of the event to update
            summary: Title of the event
            location: Location of the event
            description: Description of the event
            start_time: Start time in RFC3339 format or datetime
            end_time: End time in RFC3339 format or datetime
            attendees: List of attendees [{'email': 'person@example.com'}, ...]
            recurrence: List of recurrence rules ['RRULE:FREQ=DAILY;COUNT=2', ...]
            color_id: Color ID for the event
            reminders: Reminder settings {'useDefault': False, 'overrides': [...]}
            
        Returns:
            Dict containing updated event and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "event": None,
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # First get the current event
            event_result = self.get_event(calendar_id, event_id)
            if event_result["error"]:
                return event_result
                
            event = event_result["event"]
            
            # Update fields if provided
            if summary:
                event['summary'] = summary
                
            if location:
                event['location'] = location
                
            if description:
                event['description'] = description
                
            if start_time:
                start_datetime = self._parse_time(start_time)
                event['start'] = {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': DEFAULT_TIMEZONE,
                }
                
            if end_time:
                end_datetime = self._parse_time(end_time)
                event['end'] = {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': DEFAULT_TIMEZONE,
                }
                
            if attendees:
                event['attendees'] = attendees
                
            if recurrence:
                event['recurrence'] = recurrence
                
            if color_id:
                event['colorId'] = color_id
                
            if reminders:
                event['reminders'] = reminders
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"Successfully updated event: {updated_event.get('summary')}")
            return {
                "event": updated_event,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error updating event {event_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "event": None,
                "error": error_msg
            }
    
    def delete_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        """Delete an event.
        
        Args:
            calendar_id: ID of the calendar (use 'primary' for primary calendar)
            event_id: ID of the event to delete
            
        Returns:
            Dict containing success status and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "success": False,
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # Delete the event
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Successfully deleted event: {event_id}")
            return {
                "success": True,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error deleting event {event_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
    
    def find_free_busy(self, calendar_ids: List[str], 
                       start_time: str, end_time: str, 
                       timezone: str = DEFAULT_TIMEZONE) -> Dict[str, Any]:
        """Check free/busy information for calendars in a specific time range.
        
        Args:
            calendar_ids: List of calendar IDs to check
            start_time: Start time in RFC3339 format or datetime
            end_time: End time in RFC3339 format or datetime
            timezone: Timezone for the query
            
        Returns:
            Dict containing free/busy information and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "calendars": {},
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        try:
            # Convert times to RFC3339 if needed
            start_datetime = self._parse_time(start_time)
            end_datetime = self._parse_time(end_time)
            
            # Create request body
            body = {
                "timeMin": start_datetime.isoformat(),
                "timeMax": end_datetime.isoformat(),
                "timeZone": timezone,
                "items": [{"id": calendar_id} for calendar_id in calendar_ids]
            }
            
            # Make the freebusy query
            freebusy = self.service.freebusy().query(body=body).execute()
            
            logger.info(f"Successfully queried free/busy information for {len(calendar_ids)} calendars")
            return {
                "calendars": freebusy.get('calendars', {}),
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error finding free/busy information: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "calendars": {},
                "error": error_msg
            }
    
    def quick_add_event(self, calendar_id: str = 'primary', text: str = None) -> Dict[str, Any]:
        """Quickly add an event using natural language processing.
        
        Args:
            calendar_id: ID of the calendar (use 'primary' for primary calendar)
            text: Text describing the event (e.g., "Meeting with John tomorrow at 3pm")
            
        Returns:
            Dict containing created event and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "event": None,
                    "error": "Failed to authenticate with Google Calendar"
                }
        
        if not text:
            return {
                "event": None,
                "error": "Text describing the event is required"
            }
        
        try:
            # Use the quickAdd method
            created_event = self.service.events().quickAdd(
                calendarId=calendar_id,
                text=text
            ).execute()
            
            logger.info(f"Successfully quick-added event: {created_event.get('summary')}")
            return {
                "event": created_event,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error quick-adding event: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "event": None,
                "error": error_msg
            }
    
    def _parse_time(self, time_str):
        """Parse time string to datetime object.
        
        Handles both RFC3339 strings and datetime objects
        """
        if isinstance(time_str, datetime):
            return time_str
        
        try:
            return parse(time_str)
        except Exception as e:
            logger.error(f"Error parsing time string '{time_str}': {e}")
            raise ValueError(f"Invalid time format: {time_str}")

# Create global helper instance
def initialize_calendar_helper(scopes, token_path, credentials_path):
    """Initialize and return a global calendar helper instance"""
    global calendar_helper
    calendar_helper = GoogleCalendarHelper(scopes, token_path, credentials_path)
    return calendar_helper

# Function to ensure helper is authenticated
def ensure_authenticated() -> Dict[str, Any]:
    """Ensure that the calendar helper is authenticated.
    
    Returns:
        Dict with success status and any error message
    """
    if not calendar_helper.service:
        success = calendar_helper.authenticate()
        if not success:
            return {
                "success": False,
                "error": "Failed to authenticate with Google Calendar"
            }
    
    return {
        "success": True,
        "error": None
    }

# Import from config and initialize global helper
try:
    calendar_helper = initialize_calendar_helper(CALENDAR_SCOPES, TOKEN_PATH, CREDENTIALS_PATH)
except ImportError:
    logger.warning("Could not import from config. Using default values.")
    # Default values if config not available
    calendar_helper = GoogleCalendarHelper(
        scopes=['https://www.googleapis.com/auth/calendar'],
        token_path=Path(__file__).parent / 'token.json',
        credentials_path=Path(__file__).parent / 'credentials.json'
    ) 