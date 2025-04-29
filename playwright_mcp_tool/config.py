#!/usr/bin/env python
"""
Configuration settings for Playwright MCP tools
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# MCP Server settings
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
PLAYWRIGHT_MCP_PORT = int(os.getenv("PLAYWRIGHT_MCP_PORT", "8931"))
PLAYWRIGHT_MCP_URL = f"http://{MCP_HOST}:{PLAYWRIGHT_MCP_PORT}/sse"

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
        'playwright_mcp_server': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'playwright_mcp_agent': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}

# System prompts
SYSTEM_PROMPTS = {
    'playwright_agent': """
    You are a helpful Playwright automation assistant. Your job is to automate browser tasks.
    Focus on these key capabilities:
    
    1. Browser control (launch, navigate, screenshot, close)
    2. Page interactions (click, fill, select, check, press)
    3. Page analysis (get text, attributes, count elements, check visibility)
    4. Data extraction (tables, page title, URL, content)
    5. Advanced interactions (hover, drag and drop, file upload, JavaScript execution)
    
    Provide a concise response after performing automation tasks.
    """
}

# Error messages
ERROR_MESSAGES = {
    'missing_api_key': "ERROR: OPENAI_API_KEY not found in environment variables",
    'server_connection': "Error connecting to MCP server: {error}",
    'server_not_running': "Make sure the Playwright MCP server is running at {url}",
    'browser_launch': "Could not launch browser: {error}",
    'page_navigation': "Error navigating to page: {error}",
    'element_interaction': "Error interacting with element: {error}",
    'screenshot_capture': "Error capturing screenshot: {error}",
    'data_extraction': "Error extracting data: {error}"
}
