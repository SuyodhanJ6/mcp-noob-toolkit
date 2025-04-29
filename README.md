# MCP Noob Toolkit 🧰

<div align="center">

[![Version](https://img.shields.io/badge/Version-v0.1.0-brightgreen)](https://github.com/SuyodhanJ6/mcp-noob-toolkit/releases/tag/v0.1.0)
![MCP Toolkit](https://img.shields.io/badge/MCP-Toolkit-blue)
![Python](https://img.shields.io/badge/Python-3.11+-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

Simple toolkit for building and using Model Context Protocol (MCP) tools.

## 📋 Available MCP Tools

| Tool | Description | Status |
|------|-------------|--------|
| 🔄 **Jira MCP** | Retrieve and analyze Jira issues | Available |
| 🎬 **Video MCP** | Video transcription and summarization | Available |
| ✉️ **Gmail MCP** | Gmail integration capabilities | Available |
| 📁 **Google Drive MCP** | Google Drive document management | Available |
| 🎭 **Playwright MCP** | Browser automation and web interactions | Available |

## 📖 About

This toolkit provides simple implementations for building tools that use the Model Context Protocol (MCP). MCP is a protocol that allows AI agents to interact with external tools and services.

## ⚙️ Setup

### Installation with UV (Recommended)

This project uses Python 3.11+ and we recommend using [uv](https://github.com/astral-sh/uv) for faster dependency management:

```bash
# Create virtual environment with uv
uv venv --python 3.11

# Activate the virtual environment
source .venv/bin/activate  # On Linux/Mac
# or
# .venv\Scripts\activate  # On Windows

# Install dependencies using uv
uv sync
```

### Alternative Installation with pip

If you prefer using pip:

```bash
# Create virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On Linux/Mac
# or
# .venv\Scripts\activate  # On Windows

# Install dependencies
pip install -e .
```

### Environment Variables

Copy the example environment file and update it with your credentials:

```bash
cp .env.example .env
```

Edit the `.env` file to include your credentials (Jira, OpenAI, Gmail, etc.).

## 🔄 Jira MCP Tool

<img src="https://cdn.worldvectorlogo.com/logos/jira-1.svg" alt="Jira Logo" width="30" height="30" align="left" style="margin-right: 10px"/>

The Jira MCP Tool allows AI agents to retrieve and analyze user stories from Jira through the Model Context Protocol.

### Components

- **Server**: Provides a MCP-compliant API for extracting Jira issues
- **Client**: Uses React Agent pattern to analyze user stories

### Running the Jira MCP Server

Start the server to expose Jira functionality through MCP:

```bash
python -m jira_mcp_tool.jira_mcp_server --host 127.0.0.1 --port 3003
```

The server will listen for MCP requests on the specified host and port.

### Using the Agent Client

In a separate terminal, run the agent client to analyze a Jira issue:

```bash
python -m jira_mcp_tool.agent_client JIRA-123
```

You can specify a different model:

```bash
python -m jira_mcp_tool.agent_client JIRA-123 --model gpt-4
```

The client will:
1. Connect to the MCP server
2. Extract the issue information
3. Analyze the user story
4. Provide quality score and recommendations

## 🎬 Video MCP Tool

<img src="https://cdn-icons-png.flaticon.com/512/25/25634.png" alt="Video Icon" width="30" height="30" align="left" style="margin-right: 10px"/>

The Video MCP Tool provides video transcription and summarization services using the Model Context Protocol and OpenAI's Whisper model.

### Components

- **Server**: Provides MCP-compliant API for video transcription and summarization
- **Client**: Uses a natural language interface for processing video requests

### Features

- Transcribe videos using OpenAI's Whisper model
- Summarize video transcripts using GPT models
- Summarize videos from URLs (mock implementation for demonstration)
- Natural language interface for easy use

### Running the Video MCP Server

Start the server to expose video processing capabilities through MCP:

```bash
python -m video_mcp_tool.video_mcp_server --host 127.0.0.1 --port 3004
```

The server will check for the required OpenAI API key and listen for MCP requests on the specified host and port.

### Using the Agent Client

In a separate terminal, run the agent client with your request in natural language:

```bash
python -m video_mcp_tool.agent_client "YOUR REQUEST HERE"
```

Examples:

```bash
# Transcribe a local video file
python -m video_mcp_tool.agent_client "Transcribe the video at /path/to/video.mp4"

# Summarize a local video file
python -m video_mcp_tool.agent_client "Summarize the content of the video at /path/to/video.mp4"

# Summarize a video from a URL
python -m video_mcp_tool.agent_client "Summarize the video at https://example.com/video"
```

Optional parameters:
- `--language`: Language code (e.g., "en", "fr", "es")
- `--length`: Summary length - "short", "medium", or "long"
- `--model`: LLM model to use (default: "gpt-4o-mini")

Example with parameters:
```bash
python -m video_mcp_tool.agent_client "Summarize the video at https://example.com/video" --language fr --length short --model gpt-4
```

## ✉️ Gmail MCP Tool

<img src="https://upload.wikimedia.org/wikipedia/commons/7/7e/Gmail_icon_%282020%29.svg" alt="Gmail Logo" width="30" height="30" align="left" style="margin-right: 10px"/>

The Gmail MCP Tool provides comprehensive integration with Gmail services through the Model Context Protocol, allowing AI agents to manage emails, drafts, labels, and more.

### Components

- **Server**: Provides MCP-compliant API for Gmail operations
- **Client**: Uses React Agent pattern to process natural language queries about email management

### Features

- **Message Management**: Search, list, send, and modify Gmail messages
- **Thread Management**: View and analyze conversation threads
- **Draft Management**: Create, read, update, send, and delete email drafts
- **Label Management**: Create and manage Gmail labels
- **Filter Management**: Create and list email filters
- **History Tracking**: Monitor changes to the mailbox over time
- **Authentication**: Handle OAuth authentication with Gmail

### Setting up Google API Credentials

Before using the Gmail MCP Tool, you need to set up the necessary credentials:

<div align="center">
  
#### 🔐 Creating your credentials.json file

</div>

1. **Create a Google Cloud Project**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Click "Select a project" at the top and then "New Project"
   - Name your project (e.g., "MCP Gmail Tool") and click "Create"

2. **Enable the Gmail API**:
   - In your project dashboard, go to "APIs & Services" > "Library"
   - Search for "Gmail API" and select it
   - Click "Enable"

3. **Configure OAuth Consent Screen**:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type (or "Internal" if you're in an organization)
   - Fill in required fields (App name, User support email, Developer contact info)
   - Add scopes: `https://www.googleapis.com/auth/gmail.modify` and `https://www.googleapis.com/auth/gmail.settings.basic`
   - Add your email as a test user
   - Click "Save and Continue" through all steps

4. **Create OAuth Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" and select "OAuth client ID"
   - Select "Desktop application" as the application type
   - Name your client (e.g., "Gmail MCP Client")
   - Click "Create"

5. **Download the Credentials**:
   - A dialog will show your client ID and secret
   - Click the download button (⬇️) to download your `credentials.json` file

6. **Place the Credentials File**:
   - Save the downloaded file as `credentials.json` in the `gmail_mcp_tool` directory
   - **IMPORTANT**: This file contains sensitive information - never commit it to version control
   - Ensure it's listed in your `.gitignore` file

<div align="center">
  
![Google Cloud Setup](https://img.shields.io/badge/Google_Cloud-Setup_Required-red)

</div>

The first time you run the Gmail MCP tool, it will use this credentials file to authenticate and generate a `token.json` file for future access.

### Running the Gmail MCP Server

Start the server to expose Gmail functionality through MCP:

```bash
python -m gmail_mcp_tool.gmail_mcp_server --host 127.0.0.1 --port 3005
```

The server will check for the required credentials and listen for MCP requests on the specified host and port.

### Using the Agent Client

In a separate terminal, run the agent client with your email management request:

```bash
python -m gmail_mcp_tool.agent_client "YOUR REQUEST HERE"
```

Examples:

```bash
# Check account info
python -m gmail_mcp_tool.agent_client "What's my email address?"

# Search for emails
python -m gmail_mcp_tool.agent_client "Find all unread emails from John"

# Manage drafts
python -m gmail_mcp_tool.agent_client "Create a draft email to support@example.com about my recent order"

# Manage labels
python -m gmail_mcp_tool.agent_client "Create a new label called 'Urgent' with red background"

# Track changes
python -m gmail_mcp_tool.agent_client "Show recent changes in my inbox"
```

Optional parameters:
- `--max_results`: Maximum number of results to return (default: 10)
- `--model`: LLM model to use (default: "gpt-4o-mini")

Example with parameters:
```bash
python -m gmail_mcp_tool.agent_client "Show me my latest emails" --max_results 20 --model gpt-4
```

## 📁 Google Drive MCP Tool

<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Google_Drive_icon_%282020%29.svg/2295px-Google_Drive_icon_%282020%29.svg.png" alt="Google Drive Logo" width="30" height="30" align="left" style="margin-right: 10px"/>

The Google Drive MCP Tool provides comprehensive integration with Google Drive services through the Model Context Protocol, allowing AI agents to manage files, documents, spreadsheets, presentations, and more.

### Components

- **Server**: Provides MCP-compliant API for Google Drive operations
- **Client**: Uses React Agent pattern to process natural language queries about document management

### Features

- **File Management**: List, search, upload, download, move, and delete files
- **Document Creation**: Create Google Docs, Sheets, Slides, and folders
- **Document Editing**: Edit content in Google Docs, Sheets, and Slides
- **Collaboration**: Share files with other users and set permissions
- **Authentication**: Handle OAuth authentication with Google Drive

### Setting up Google API Credentials

Before using the Google Drive MCP Tool, you need to set up the necessary credentials:

<div align="center">
  
#### 🔐 Creating your credentials.json file

</div>

1. **Create a Google Cloud Project**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Click "Select a project" at the top and then "New Project"
   - Name your project (e.g., "MCP Drive Tool") and click "Create"

2. **Enable the Google Drive API**:
   - In your project dashboard, go to "APIs & Services" > "Library"
   - Search for "Google Drive API" and select it
   - Click "Enable"
   - Also enable "Google Docs API", "Google Sheets API", and "Google Slides API" for full functionality

3. **Configure OAuth Consent Screen**:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type (or "Internal" if you're in an organization)
   - Fill in required fields (App name, User support email, Developer contact info)
   - Add scopes for Drive, Docs, Sheets, and Slides
   - Add your email as a test user
   - Click "Save and Continue" through all steps

4. **Create OAuth Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" and select "OAuth client ID"
   - Select "Desktop application" as the application type
   - Name your client (e.g., "Drive MCP Client")
   - Click "Create"

5. **Download the Credentials**:
   - A dialog will show your client ID and secret
   - Click the download button (⬇️) to download your `credentials.json` file

6. **Place the Credentials File**:
   - Save the downloaded file as `credentials.json` in the `google_drive_mcp_tool` directory
   - **IMPORTANT**: This file contains sensitive information - never commit it to version control
   - Ensure it's listed in your `.gitignore` file

<div align="center">
  
![Google Cloud Setup](https://img.shields.io/badge/Google_Cloud-Setup_Required-red)

</div>

The first time you run the Google Drive MCP tool, it will use this credentials file to authenticate and generate a `token.json` file for future access.

### Running the Google Drive MCP Server

Start the server to expose Google Drive functionality through MCP:

```bash
python -m google_drive_mcp_tool.google_drive_mcp_tool --host 127.0.0.1 --port 3006
```

The server will check for the required credentials and listen for MCP requests on the specified host and port.

### Using the Agent Client

In a separate terminal, run the agent client with your document management request:

```bash
python -m google_drive_mcp_tool.agent_client "YOUR REQUEST HERE"
```

Examples:

```bash
# List files
python -m google_drive_mcp_tool.agent_client "Show me my recent files"

# Create documents
python -m google_drive_mcp_tool.agent_client "Create a new document called 'Meeting Notes'"

# Upload files
python -m google_drive_mcp_tool.agent_client "Upload budget.xlsx to my drive"

# Share files
python -m google_drive_mcp_tool.agent_client "Share my presentation with john@example.com"

# Create folders
python -m google_drive_mcp_tool.agent_client "Create a new folder for project documents"

# Download files
python -m google_drive_mcp_tool.agent_client "Download my quarterly report PDF"

# Search for files
python -m google_drive_mcp_tool.agent_client "Search for files containing 'project plan'"
```

Optional parameters:
- `--model`: LLM model to use (default: "gpt-4o-mini")
- `--interactive`: Run in interactive mode

Interactive mode:
```bash
python -m google_drive_mcp_tool.agent_client --interactive
```

## 🎭 Playwright MCP Tool

<img src="https://playwright.dev/img/playwright-logo.svg" alt="Playwright Logo" width="30" height="30" align="left" style="margin-right: 10px"/>

The Playwright MCP Tool provides browser automation capabilities through the Model Context Protocol, allowing AI agents to interact with web pages, extract data, and perform complex web automation tasks.

### Components

- **Server**: Provides MCP-compliant API for Playwright browser automation
- **Client**: Uses React Agent pattern to process natural language queries for web automation

### Features

- **Browser Control**: Launch, navigate, and close browsers (Chromium, Firefox, WebKit)
- **Page Interaction**: Click elements, fill forms, select options, check boxes, press keys
- **Page Analysis**: Get text, attributes, count elements, check visibility, wait for selectors
- **Data Extraction**: Extract tables, get page title, URL, and content
- **Advanced Interactions**: Hover, drag and drop, upload files, execute JavaScript

### Prerequisites

You need to set up the Playwright MCP server before using the tool:

```bash
# Clone the Playwright MCP repository
git clone https://github.com/microsoft/playwright-mcp.git

# Navigate to the repository
cd playwright-mcp/

# Run the Playwright MCP server in Docker
docker run -i --rm --init -p 8931:8931 mcp/playwright
```

The server will be available at http://localhost:8931.

### Running the Playwright MCP Client

In a separate terminal, run the agent client with your web automation request:

```bash
python -m playwright_mcp_tool.agent_client "YOUR REQUEST HERE"
```

Examples:

```bash
# Basic browser operations
python -m playwright_mcp_tool.agent_client "Open Chrome and go to github.com"
python -m playwright_mcp_tool.agent_client "Take a screenshot of the current page"

# Form interactions
python -m playwright_mcp_tool.agent_client "Go to example.com and fill the search box with 'automation'"
python -m playwright_mcp_tool.agent_client "Click the Submit button"

# Data extraction
python -m playwright_mcp_tool.agent_client "Extract data from the products table on the page"
python -m playwright_mcp_tool.agent_client "Get the text of the main heading"

# Complex automation
python -m playwright_mcp_tool.agent_client "Log into my GitHub account with username 'user' and password 'pass'"
python -m playwright_mcp_tool.agent_client "Navigate to twitter.com, search for 'AI news', and extract the first 5 results"
```

You can run the client in interactive mode:

```bash
python -m playwright_mcp_tool.agent_client -i
```

Optional parameters:
- `--model`: LLM model to use (default: "gpt-4o-mini")

Example with parameters:
```bash
python -m playwright_mcp_tool.agent_client "Automate login to my account" --model gpt-4
```

## 🛠️ Extending the Toolkit

You can extend this toolkit by:

1. Adding new MCP tools to the server
2. Implementing more sophisticated clients that use LLMs for analysis
3. Creating new MCP servers for other services

## 📄 License

MIT



