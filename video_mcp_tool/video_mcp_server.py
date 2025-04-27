#!/usr/bin/env python
"""
Video MCP Server - Provides video transcription and summarization services via MCP protocol.
"""

import os
import sys
import tempfile
import base64
from typing import Optional, Dict, Any
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
import openai
from dotenv import load_dotenv
import moviepy.editor as mp
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport
import uvicorn
import requests

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create MCP server
mcp = FastMCP("VideoTools")

class VideoTranscriptionRequest(BaseModel):
    video_data_base64: Optional[str] = None
    video_path: Optional[str] = None

class VideoTranscriptionResponse(BaseModel):
    transcript: str
    error: Optional[str] = None

class VideoSummarizationRequest(BaseModel):
    video_url: str
    language: Optional[str] = "en"
    length: Optional[str] = "medium"  # short, medium, long

class VideoSummarizationResponse(BaseModel):
    summary: str
    error: Optional[str] = None

@mcp.tool()
async def transcribe_video(request: VideoTranscriptionRequest) -> VideoTranscriptionResponse:
    """
    Transcribe a video file using OpenAI's Whisper model.
    
    Args:
        request: An object containing either base64-encoded video data or a file path.
        
    Returns:
        An object containing the transcript and any error messages.
    """
    try:
        temp_audio = None
        temp_video = None
        
        if request.video_data_base64:
            # Decode base64 video data
            video_data = base64.b64decode(request.video_data_base64)
            
            # Create temporary video file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video_file:
                temp_video = temp_video_file.name
                temp_video_file.write(video_data)
            
            video_path = temp_video
        elif request.video_path:
            # Use provided video path
            video_path = request.video_path
            
            # Verify file exists
            if not os.path.exists(video_path):
                return VideoTranscriptionResponse(
                    transcript="",
                    error=f"Video file does not exist at path: {video_path}"
                )
        else:
            return VideoTranscriptionResponse(
                transcript="",
                error="Either video_data_base64 or video_path must be provided"
            )
        
        # Extract audio from video
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio_file:
            temp_audio = temp_audio_file.name
        
        video = mp.VideoFileClip(video_path)
        video.audio.write_audiofile(temp_audio, verbose=False, logger=None)
        
        # Transcribe audio using OpenAI's Whisper model
        with open(temp_audio, "rb") as audio_file:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        transcript_text = transcription.text
        
        return VideoTranscriptionResponse(transcript=transcript_text)
        
    except Exception as e:
        return VideoTranscriptionResponse(
            transcript="",
            error=f"Error transcribing video: {str(e)}"
        )
    finally:
        # Clean up temporary files
        if temp_audio and os.path.exists(temp_audio):
            os.unlink(temp_audio)
        if temp_video and os.path.exists(temp_video):
            os.unlink(temp_video)

@mcp.tool()
async def summarize_video_transcript(transcript: str) -> str:
    """
    Summarize a video transcript using GPT.
    
    Args:
        transcript: The transcript text to summarize
        
    Returns:
        A summary of the transcript
    """
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes video transcripts."},
                {"role": "user", "content": f"Please summarize the following transcript concisely:\n\n{transcript}"}
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error summarizing transcript: {str(e)}"

@mcp.tool()
async def summarize_video(request: VideoSummarizationRequest) -> VideoSummarizationResponse:
    """
    Summarize a video from a given URL.
    
    Args:
        request: An object containing the video URL and optional parameters.
        
    Returns:
        An object containing the summary and any error messages.
    """
    try:
        # Get API key from environment variables
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            error_msg = "OPENAI_API_KEY not found in environment variables"
            print(f"ERROR: {error_msg}")
            return VideoSummarizationResponse(
                summary="",
                error=error_msg
            )
        
        print(f"Processing video URL: {request.video_url}")
        print(f"Parameters - Language: {request.language}, Length: {request.length}")
        
        # For now, return a mock response
        # In production, you would download the video, transcribe it, and then summarize
        
        # Mock summary based on URL
        mock_summary = f"This is a mock summary of the video at {request.video_url}. "
        mock_summary += "The video discusses key concepts in artificial intelligence and machine learning. "
        mock_summary += "It covers topics like neural networks, deep learning, and practical applications. "
        mock_summary += f"This summary is in {request.language} language and is of {request.length} length."
        
        return VideoSummarizationResponse(
            summary=mock_summary
        )
        
    except Exception as e:
        error_msg = f"Error summarizing video: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        print(traceback.format_exc())
        return VideoSummarizationResponse(
            summary="",
            error=error_msg
        )

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

    # Check API credentials at startup
    api_key = os.getenv("OPENAI_API_KEY")
    
    print("\nVideo MCP Server - Credential Check:")
    if api_key:
        print("✓ OPENAI_API_KEY: Present (not showing for security)")
    else:
        print("✗ OPENAI_API_KEY: Not found in environment variables")
    
    # Get MCP server instance from FastMCP
    mcp_server = mcp._mcp_server

    parser = argparse.ArgumentParser(description="Video MCP Server")
    parser.add_argument("--port", type=int, default=3004, help="Port for server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for server")
    
    args = parser.parse_args()
    
    print(f"\nStarting Video MCP Server on {args.host}:{args.port}")
    
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