#!/usr/bin/env python
"""
Configuration settings for Google Calendar MCP tools
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Google Calendar API settings
CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.settings.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events.readonly'
]
TOKEN_PATH = BASE_DIR / 'token.json'
CREDENTIALS_PATH = BASE_DIR / 'credentials.json'

# Default timezone (India/Mumbai)
DEFAULT_TIMEZONE = "Asia/Kolkata"

# MCP Server settings
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
CALENDAR_MCP_PORT = int(os.getenv("CALENDAR_MCP_PORT", "3007"))
CALENDAR_MCP_URL = f"http://{MCP_HOST}:{CALENDAR_MCP_PORT}/sse"

# Agent settings
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
DEFAULT_MAX_RESULTS = int(os.getenv("DEFAULT_MAX_RESULTS", "10"))

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'DEBUG',
            'stream': 'ext://sys.stdout'
        },
    },
    'loggers': {
        'gcalendar_mcp_server': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'gcalendar_mcp_agent': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'gcalendar_helper': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}

# Calendar color IDs
COLOR_IDS = {
    'blue': '1',
    'green': '2',
    'purple': '3',
    'red': '4',
    'yellow': '5',
    'orange': '6',
    'turquoise': '7',
    'gray': '8',
    'bold blue': '9',
    'bold green': '10',
    'bold red': '11'
}

# Event reminder methods
REMINDER_METHODS = {
    'email': 'email',
    'popup': 'popup',
}

# System prompts
SYSTEM_PROMPTS = {
    'agent': """
    You are a helpful Google Calendar analyst and organizer. Your job is to analyze calendar events and provide scheduling assistance.
    Focus on these key elements:
    
    1. Event organization and scheduling
    2. Calendar management and availability
    3. Event details and attendees
    4. Time management and optimization
    
    Provide concise analysis of calendar data, highlight important information, and suggest scheduling improvements.
    """
}

# Error messages
ERROR_MESSAGES = {
    'missing_api_key': "ERROR: OPENAI_API_KEY not found in environment variables",
    'server_connection': "Error connecting to MCP server: {error}",
    'server_not_running': "Make sure the Google Calendar MCP server is running at {url}",
    'event_retrieval': "Could not retrieve events",
    'event_creation': "Error creating event: {error}",
    'authentication_error': "Authentication failed: {error}",
    'api_not_enabled': "{api_name} API is not enabled in your Google Cloud project. Enable it at: {enable_url}"
} 