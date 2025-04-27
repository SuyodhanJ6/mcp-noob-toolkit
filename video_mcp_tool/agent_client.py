#!/usr/bin/env python3
"""
Video MCP Agent Client - Simple client for processing videos using react_agent
"""

import os
import asyncio
import argparse
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LangChain MCP adapter imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

class VideoProcessor:
    """Simple agent for processing videos using React Agent"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """Initialize the video processor.
        
        Args:
            model_name: The name of the LLM model to use
        """
        self.model_name = model_name
        self.llm = None
        self.agent = None
        self.mcp_client = None
        self.system_prompt = """
        You are a helpful video processing assistant. Your job is to process videos based on user requests.
        
        You have access to these tools:
        - VideoTools.transcribe_video: Transcribe a video file from a local path
        - VideoTools.summarize_video_transcript: Summarize a video transcript
        - VideoTools.summarize_video: Summarize a video from a URL
        
        Based on the user's request, choose the appropriate tool(s) and process the video.
        If they want a transcript, use transcribe_video.
        If they want a summary and provide a URL, use summarize_video.
        If they want a summary of a local file, first transcribe it, then summarize the transcript.
        
        Always be helpful, concise, and provide clear results.
        """
    
    async def setup(self):
        """Set up the agent with the MCP tools."""
        # Initialize the LLM
        self.llm = ChatOpenAI(model=self.model_name, api_key=os.getenv("OPENAI_API_KEY"))
        
        # Get MCP server URL from environment
        mcp_host = os.getenv("MCP_HOST", "127.0.0.1")
        video_mcp_port = os.getenv("VIDEO_MCP_PORT", "3004")
        mcp_url = f"http://{mcp_host}:{video_mcp_port}/sse"
        
        try:
            # Connect to the Video MCP server
            self.mcp_client = MultiServerMCPClient(
                {
                    "videotools": {
                        "url": mcp_url,
                        "transport": "sse",
                    }
                }
            )
            
            await self.mcp_client.__aenter__()
            
            # Get tools from the MCP server
            mcp_tools = self.mcp_client.get_tools()
            print(f"Loaded {len(mcp_tools)} tools from MCP servers")
            
            # Create a simple React agent
            self.agent = create_react_agent(
                self.llm,
                mcp_tools,
                prompt=self.system_prompt
            )
        except Exception as e:
            print(f"Error connecting to MCP server: {str(e)}")
            print(f"Make sure the Video MCP server is running at {mcp_url}")
            raise
    
    async def process_request(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a video request.
        
        Args:
            request: The user's request describing what they want to do with the video
            **kwargs: Additional parameters like language, model, etc.
            
        Returns:
            Processing results
        """
        if not self.agent:
            await self.setup()
        
        try:
            print(f"Processing request: {request}")
            
            # Create a prompt that includes the user's request and any additional parameters
            params_str = ""
            for key, value in kwargs.items():
                if value:
                    params_str += f"\n- {key}: {value}"
            
            if params_str:
                prompt = f"{request}\n\nAdditional parameters:{params_str}"
            else:
                prompt = request
            
            # Let the agent decide what to do
            result = await self.agent.ainvoke({
                "messages": [
                    HumanMessage(content=prompt)
                ]
            })
            
            return result
        
        except Exception as e:
            return {
                "error": f"Error processing request: {str(e)}"
            }
    
    async def close(self):
        """Clean up resources."""
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)


async def main():
    """Run the video processor."""
    parser = argparse.ArgumentParser(description="Video Processor Agent")
    parser.add_argument("request", help="What do you want to do with the video? (e.g., 'Transcribe the video at path/to/video.mp4' or 'Summarize the video at https://example.com/video')")
    parser.add_argument("--language", help="Language for processing (default: en)")
    parser.add_argument("--length", choices=["short", "medium", "long"], 
                        help="Desired length of summary (if applicable)")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model to use")
    
    args = parser.parse_args()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found in environment variables")
        print("Please set it in your .env file")
        return
    
    processor = VideoProcessor(model_name=args.model)
    
    try:
        # Process the request
        result = await processor.process_request(
            args.request,
            language=args.language,
            length=args.length
        )
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
        
        # Display the result
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if ai_messages:
            print("\n===== RESULT =====")
            print(ai_messages[-1].content)
        else:
            print("No output was generated")
    
    finally:
        # Clean up
        await processor.close()


if __name__ == "__main__":
    asyncio.run(main()) 