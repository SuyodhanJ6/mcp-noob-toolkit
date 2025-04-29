#!/usr/bin/env python
"""
Configuration settings for Google Drive MCP tools
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Google Drive API settings
DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.appdata',
    'https://www.googleapis.com/auth/drive.metadata',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations'
]
TOKEN_PATH = BASE_DIR / 'token.json'
CREDENTIALS_PATH = BASE_DIR / 'credentials.json'

# MCP Server settings
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
DRIVE_MCP_PORT = int(os.getenv("DRIVE_MCP_PORT", "3006"))
DRIVE_MCP_URL = f"http://{MCP_HOST}:{DRIVE_MCP_PORT}/sse"

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
        'gdrive_mcp_server': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'gdrive_mcp_agent': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'gdrive_helper': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}

# File types and MIME types
MIME_TYPES = {
    'folder': 'application/vnd.google-apps.folder',
    'document': 'application/vnd.google-apps.document',
    'spreadsheet': 'application/vnd.google-apps.spreadsheet',
    'presentation': 'application/vnd.google-apps.presentation',
    'pdf': 'application/pdf',
    'text': 'text/plain',
    'csv': 'text/csv',
    'word': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'powerpoint': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image': 'image/jpeg'
}

# System prompts
SYSTEM_PROMPTS = {
    'agent': """
    You are a helpful Google Drive file analyzer. Your job is to analyze files and provide insights.
    Focus on these key elements:
    
    1. File organization and structure
    2. Document content analysis
    3. Collaboration patterns and sharing settings
    4. File metadata and properties
    
    Provide a concise analysis of the files, highlighting important information and suggesting organization improvements.
    """
}

# Error messages
ERROR_MESSAGES = {
    'missing_api_key': "ERROR: OPENAI_API_KEY not found in environment variables",
    'server_connection': "Error connecting to MCP server: {error}",
    'server_not_running': "Make sure the Google Drive MCP server is running at {url}",
    'file_retrieval': "Could not retrieve files",
    'file_analysis': "Error analyzing files: {error}",
    'authentication_error': "Authentication failed: {error}",
    'api_not_enabled': "{api_name} API is not enabled in your Google Cloud project. Enable it at: {enable_url}"
}
