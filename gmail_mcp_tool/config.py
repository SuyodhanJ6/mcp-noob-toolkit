#!/usr/bin/env python
"""
Configuration settings for Gmail MCP tools
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Gmail API settings
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.metadata',
    'https://www.googleapis.com/auth/gmail.modify'
]
TOKEN_PATH = BASE_DIR / 'token.json'
CREDENTIALS_PATH = BASE_DIR / 'credentials.json'

# MCP Server settings
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
GMAIL_MCP_PORT = int(os.getenv("GMAIL_MCP_PORT", "3005"))
GMAIL_MCP_URL = f"http://{MCP_HOST}:{GMAIL_MCP_PORT}/sse"

# Agent settings
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
DEFAULT_MAX_RESULTS = int(os.getenv("DEFAULT_MAX_RESULTS", "5"))

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
        'gmail_mcp_server': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'gmail_mcp_agent': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}

# System prompts
SYSTEM_PROMPTS = {
    'agent': """
    You are a helpful Gmail message analyzer. Your job is to analyze email messages and provide insights.
    Focus on these key elements:
    
    1. Message importance and urgency
    2. Key topics and subjects
    3. Action items or follow-ups needed
    4. Sentiment and tone
    
    Provide a concise analysis of the messages, highlighting important information and suggesting next steps.
    """
}

# Error messages
ERROR_MESSAGES = {
    'missing_api_key': "ERROR: OPENAI_API_KEY not found in environment variables",
    'server_connection': "Error connecting to MCP server: {error}",
    'server_not_running': "Make sure the Gmail MCP server is running at {url}",
    'message_retrieval': "Could not retrieve messages",
    'message_analysis': "Error analyzing messages: {error}"
}
