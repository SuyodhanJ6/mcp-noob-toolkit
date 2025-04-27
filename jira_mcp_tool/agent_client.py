#!/usr/bin/env python3
"""
Jira MCP Agent Client - Simple client for analyzing Jira issues using react_agent
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

class JiraIssueAnalyzer:
    """Simple agent for analyzing Jira issues using React Agent"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """Initialize the Jira issue analyzer.
        
        Args:
            model_name: The name of the LLM model to use
        """
        self.model_name = model_name
        self.llm = None
        self.agent = None
        self.mcp_client = None
        self.system_prompt = """
        You are a helpful Jira issue analyst. Your job is to analyze user stories and suggest improvements.
        Focus on these key elements:
        
        1. Is this formatted as a proper user story ("As a [user], I want [action], so that [benefit]")?
        2. Does it have acceptance criteria?
        3. Is it clear and specific?
        
        Give a simple quality score (1-5) and brief suggestions for improvement.
        Keep your analysis concise and practical.
        """
    
    async def setup(self):
        """Set up the agent with the MCP tools."""
        # Initialize the LLM
        self.llm = ChatOpenAI(model=self.model_name, api_key=os.getenv("OPENAI_API_KEY"))
        
        # Get MCP server URL from environment
        mcp_host = os.getenv("MCP_HOST", "127.0.0.1")
        jira_mcp_port = os.getenv("JIRA_MCP_PORT", "3003")
        mcp_url = f"http://{mcp_host}:{jira_mcp_port}/sse"
        
        try:
            # Connect to the Jira MCP server
            self.mcp_client = MultiServerMCPClient(
                {
                    "jiratools": {
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
            print(f"Make sure the Jira MCP server is running at {mcp_url}")
            raise
    
    async def analyze_issue(self, issue_key: str) -> Dict[str, Any]:
        """Analyze a Jira issue.
        
        Args:
            issue_key: The Jira issue key (e.g., "SCRUM-123")
            
        Returns:
            Analysis results
        """
        if not self.agent:
            await self.setup()
        
        try:
            print(f"Analyzing Jira issue: {issue_key}")
            
            # Extract the issue first
            extract_prompt = f"Please extract the summary and description from Jira issue {issue_key} using the JiraTools.extract_jira_issue tool."
            
            extract_result = await self.agent.ainvoke({
                "messages": [
                    HumanMessage(content=extract_prompt)
                ]
            })
            
            # Check if we got a response
            ai_messages = [msg for msg in extract_result["messages"] if isinstance(msg, AIMessage)]
            if not ai_messages:
                return {
                    "error": f"Could not extract information from issue {issue_key}"
                }
            
            # Get the content from the AI's response
            last_message = ai_messages[-1].content
            
            # Now analyze it
            analysis_prompt = f"""
            Analyze this Jira issue and provide a simple assessment:
            
            {last_message}
            
            Please include:
            1. Is this a well-formed user story?
            2. Quality score (1-5)
            3. 2-3 key recommendations for improvement
            
            Keep your response concise.
            """
            
            analysis_result = await self.agent.ainvoke({
                "messages": extract_result["messages"] + [
                    HumanMessage(content=analysis_prompt)
                ]
            })
            
            return analysis_result
        
        except Exception as e:
            return {
                "error": f"Error analyzing issue: {str(e)}"
            }
    
    async def close(self):
        """Clean up resources."""
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)


async def main():
    """Run the Jira issue analyzer."""
    parser = argparse.ArgumentParser(description="Jira Issue Analyzer")
    parser.add_argument("issue_key", help="Jira issue key (e.g., SCRUM-123)")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model to use")
    args = parser.parse_args()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found in environment variables")
        print("Please set it in your .env file")
        return
    
    analyzer = JiraIssueAnalyzer(model_name=args.model)
    
    try:
        # Analyze the issue
        result = await analyzer.analyze_issue(args.issue_key)
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
        
        # Display the analysis result
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if ai_messages:
            print("\n===== JIRA ISSUE ANALYSIS =====")
            print(ai_messages[-1].content)
        else:
            print("No analysis was generated")
    
    finally:
        # Clean up
        await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())
