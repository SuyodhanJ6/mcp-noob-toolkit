# MCP Noob Toolkit

Toolkit for building Model Context Protocol (MCP) tools.

## About

This toolkit provides simple implementations for building tools that use the Model Context Protocol (MCP). MCP is a protocol that allows AI agents to interact with external tools and services.

## Setup

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

Edit the `.env` file to include your Jira and OpenAI credentials.

## Jira MCP Tool

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

## Video MCP Tool

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

## Extending the Toolkit

You can extend this toolkit by:

1. Adding new MCP tools to the server
2. Implementing more sophisticated clients that use LLMs for analysis
3. Creating new MCP servers for other services

## License

MIT



