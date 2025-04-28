#!/usr/bin/env python
"""
Gmail MCP Server - Provides Gmail message listing and analysis services via MCP protocol.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport
import uvicorn
import logging
import logging.config

# Import configurations and helper
from config import (
    LOGGING_CONFIG,
    MCP_HOST,
    GMAIL_MCP_PORT
)
from helper import gmail_helper, ensure_authenticated

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('gmail_mcp_server')

# Create MCP server
mcp = FastMCP("GmailTools")

# -------------------------------------------------------------------------
# Message Listing Tool
# -------------------------------------------------------------------------

class GmailMessageRequest(BaseModel):
    query: Optional[str] = ""
    max_results: Optional[int] = 10

class GmailMessageResponse(BaseModel):
    messages: List[Dict[str, Any]]
    error: Optional[str] = None

@mcp.tool()
async def list_gmail_messages(request: GmailMessageRequest) -> GmailMessageResponse:
    """
    List Gmail messages based on the provided query.
    
    Args:
        request: An object containing the search query and max results.
        
    Returns:
        An object containing the messages and any error messages.
    """
    try:
        logger.info(f"Listing Gmail messages with query: {request.query}")
        
        # Use helper to get messages
        result = gmail_helper.list_messages(
            query=request.query,
            max_results=request.max_results
        )
        
        if result["error"]:
            logger.error(result["error"])
            return GmailMessageResponse(
                messages=[],
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved {len(result['messages'])} messages")
        return GmailMessageResponse(
            messages=result["messages"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in list_gmail_messages: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return GmailMessageResponse(messages=[], error=error_msg)

# -------------------------------------------------------------------------
# User Profile Tool (getProfile)
# -------------------------------------------------------------------------

class GmailProfileRequest(BaseModel):
    user_id: Optional[str] = 'me'

class GmailProfileResponse(BaseModel):
    profile: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def get_gmail_profile(request: GmailProfileRequest) -> GmailProfileResponse:
    """
    Retrieve basic profile information about the authenticated Gmail user.
    
    This tool uses the Gmail API's users.getProfile method to fetch basic information
    about the user's Gmail account, including email address, total message count,
    and storage usage.
    
    Args:
        request: An object containing the user_id (defaults to 'me' for authenticated user).
        
    Returns:
        An object containing the profile information and any error messages.
    """
    try:
        logger.info(f"Retrieving Gmail profile for user: {request.user_id}")
        
        # Use helper to get profile
        result = gmail_helper.get_profile(user_id=request.user_id)
        
        if result["error"]:
            logger.error(result["error"])
            return GmailProfileResponse(
                profile=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved profile for {result['profile'].get('emailAddress')}")
        return GmailProfileResponse(
            profile=result["profile"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_gmail_profile: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return GmailProfileResponse(profile=None, error=error_msg)

# -------------------------------------------------------------------------
# Watch Tool (watch)
# -------------------------------------------------------------------------

class GmailWatchRequest(BaseModel):
    topic_name: str  # Required: Google Cloud Pub/Sub topic
    label_ids: Optional[List[str]] = None
    user_id: Optional[str] = 'me'

class GmailWatchResponse(BaseModel):
    watch_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def setup_gmail_watch(request: GmailWatchRequest) -> GmailWatchResponse:
    """
    Set up push notifications for a user's mailbox changes.
    
    This tool configures Gmail to send notifications to your application when 
    changes occur in the user's mailbox. It requires a Google Cloud Pub/Sub topic 
    where notifications will be sent.
    
    Args:
        request: An object containing:
            - topic_name: Google Cloud Pub/Sub topic (required)
            - label_ids: List of Gmail label IDs to watch (optional, defaults to ['INBOX'])
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing watch setup data (including expiration time and historyId) 
        and any error messages.
    """
    try:
        logger.info(f"Setting up Gmail watch for user: {request.user_id} on topic: {request.topic_name}")
        
        # Use helper to setup watch
        result = gmail_helper.setup_watch(
            topic_name=request.topic_name,
            label_ids=request.label_ids,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return GmailWatchResponse(
                watch_data=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully set up Gmail watch. Expires: {result['watch_data'].get('expiration')}")
        return GmailWatchResponse(
            watch_data=result["watch_data"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in setup_gmail_watch: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return GmailWatchResponse(watch_data=None, error=error_msg)

# -------------------------------------------------------------------------
# Draft Management Tools
# -------------------------------------------------------------------------

# Create Draft Tool
class CreateDraftRequest(BaseModel):
    to: str
    subject: str
    message_text: str
    user_id: Optional[str] = 'me'

class DraftResponse(BaseModel):
    draft: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def create_gmail_draft(request: CreateDraftRequest) -> DraftResponse:
    """
    Create a new draft email.
    
    This tool saves a new message as a draft with the DRAFT label. The draft is created
    in the authenticated user's mailbox.
    
    Args:
        request: An object containing:
            - to: Email recipient(s)
            - subject: Email subject
            - message_text: Email body content
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the created draft data and any error messages.
    """
    try:
        logger.info(f"Creating draft email to: {request.to}")
        
        # Get user's email for the 'from' field
        profile_result = gmail_helper.get_profile(user_id=request.user_id)
        if profile_result["error"]:
            return DraftResponse(
                draft=None,
                error=f"Failed to get user profile: {profile_result['error']}"
            )
        
        sender = profile_result["profile"]["emailAddress"]
        
        # Create message body
        message_body = gmail_helper.create_message(
            sender=sender,
            to=request.to,
            subject=request.subject,
            message_text=request.message_text
        )
        
        # Create draft
        result = gmail_helper.create_draft(
            message_body=message_body,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DraftResponse(
                draft=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully created draft with ID: {result['draft']['id']}")
        return DraftResponse(
            draft=result["draft"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in create_gmail_draft: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DraftResponse(draft=None, error=error_msg)

# Delete Draft Tool
class DeleteDraftRequest(BaseModel):
    draft_id: str
    user_id: Optional[str] = 'me'

class DeleteDraftResponse(BaseModel):
    success: bool
    error: Optional[str] = None

@mcp.tool()
async def delete_gmail_draft(request: DeleteDraftRequest) -> DeleteDraftResponse:
    """
    Permanently delete a draft email.
    
    This tool immediately removes the specified draft from the user's mailbox.
    
    Args:
        request: An object containing:
            - draft_id: ID of the draft to delete
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object indicating success or failure and any error messages.
    """
    try:
        logger.info(f"Deleting draft with ID: {request.draft_id}")
        
        # Delete draft
        result = gmail_helper.delete_draft(
            draft_id=request.draft_id,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DeleteDraftResponse(
                success=False,
                error=result["error"]
            )
        
        logger.info(f"Successfully deleted draft {request.draft_id}")
        return DeleteDraftResponse(
            success=True,
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in delete_gmail_draft: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DeleteDraftResponse(success=False, error=error_msg)

# Get Draft Tool
class GetDraftRequest(BaseModel):
    draft_id: str
    user_id: Optional[str] = 'me'
    format: Optional[str] = 'full'

@mcp.tool()
async def get_gmail_draft(request: GetDraftRequest) -> DraftResponse:
    """
    Retrieve a specific draft email.
    
    This tool fetches details of a specific draft, including its message content.
    
    Args:
        request: An object containing:
            - draft_id: ID of the draft to retrieve
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
            - format: Format of the message (optional, defaults to 'full')
        
    Returns:
        An object containing the draft data and any error messages.
    """
    try:
        logger.info(f"Retrieving draft with ID: {request.draft_id}")
        
        # Get draft
        result = gmail_helper.get_draft(
            draft_id=request.draft_id,
            user_id=request.user_id,
            format=request.format
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DraftResponse(
                draft=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved draft {request.draft_id}")
        return DraftResponse(
            draft=result["draft"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_gmail_draft: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DraftResponse(draft=None, error=error_msg)

# List Drafts Tool
class ListDraftsRequest(BaseModel):
    user_id: Optional[str] = 'me'
    max_results: Optional[int] = 10

class ListDraftsResponse(BaseModel):
    drafts: List[Dict[str, Any]]
    error: Optional[str] = None

@mcp.tool()
async def list_gmail_drafts(request: ListDraftsRequest) -> ListDraftsResponse:
    """
    List all draft emails in the user's mailbox.
    
    This tool returns information about drafts in the user's mailbox,
    including details like recipients, subject, and message content.
    
    Args:
        request: An object containing:
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
            - max_results: Maximum number of drafts to return (optional, defaults to 10)
        
    Returns:
        An object containing a list of drafts and any error messages.
    """
    try:
        logger.info(f"Listing drafts for user: {request.user_id}")
        
        # List drafts
        result = gmail_helper.list_drafts(
            user_id=request.user_id,
            max_results=request.max_results
        )
        
        if result["error"]:
            logger.error(result["error"])
            return ListDraftsResponse(
                drafts=[],
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved {len(result['drafts'])} drafts")
        return ListDraftsResponse(
            drafts=result["drafts"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in list_gmail_drafts: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ListDraftsResponse(drafts=[], error=error_msg)

# Send Draft Tool
class SendDraftRequest(BaseModel):
    draft_id: str
    user_id: Optional[str] = 'me'

class SendDraftResponse(BaseModel):
    message: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def send_gmail_draft(request: SendDraftRequest) -> SendDraftResponse:
    """
    Send an existing draft email.
    
    This tool takes a draft and sends it as an email to the recipients. The draft
    is removed from the drafts folder after sending.
    
    Args:
        request: An object containing:
            - draft_id: ID of the draft to send
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the sent message data and any error messages.
    """
    try:
        logger.info(f"Sending draft with ID: {request.draft_id}")
        
        # Send draft
        result = gmail_helper.send_draft(
            draft_id=request.draft_id,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return SendDraftResponse(
                message=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully sent draft {request.draft_id}")
        return SendDraftResponse(
            message=result["message"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in send_gmail_draft: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return SendDraftResponse(message=None, error=error_msg)

# Update Draft Tool
class UpdateDraftRequest(BaseModel):
    draft_id: str
    to: str
    subject: str
    message_text: str
    user_id: Optional[str] = 'me'

@mcp.tool()
async def update_gmail_draft(request: UpdateDraftRequest) -> DraftResponse:
    """
    Update the content of an existing draft email.
    
    This tool replaces the content of an existing draft with new content.
    
    Args:
        request: An object containing:
            - draft_id: ID of the draft to update
            - to: New email recipient(s)
            - subject: New email subject
            - message_text: New email body content
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the updated draft data and any error messages.
    """
    try:
        logger.info(f"Updating draft with ID: {request.draft_id}")
        
        # Get user's email for the 'from' field
        profile_result = gmail_helper.get_profile(user_id=request.user_id)
        if profile_result["error"]:
            return DraftResponse(
                draft=None,
                error=f"Failed to get user profile: {profile_result['error']}"
            )
        
        sender = profile_result["profile"]["emailAddress"]
        
        # Create new message body
        message_body = gmail_helper.create_message(
            sender=sender,
            to=request.to,
            subject=request.subject,
            message_text=request.message_text
        )
        
        # Update draft
        result = gmail_helper.update_draft(
            draft_id=request.draft_id,
            message_body=message_body,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DraftResponse(
                draft=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully updated draft {request.draft_id}")
        return DraftResponse(
            draft=result["draft"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in update_gmail_draft: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DraftResponse(draft=None, error=error_msg)

# -------------------------------------------------------------------------
# Gmail History Tool
# -------------------------------------------------------------------------

class HistoryRequest(BaseModel):
    start_history_id: Optional[str] = None
    history_types: Optional[List[str]] = None
    max_results: Optional[int] = 100
    user_id: Optional[str] = 'me'

class HistoryResponse(BaseModel):
    history_records: List[Dict[str, Any]] = []
    latest_history_id: Optional[str] = None
    error: Optional[str] = None

class LoadHistoryIdResponse(BaseModel):
    history_id: Optional[str] = None
    error: Optional[str] = None

@mcp.tool()
async def load_saved_history_id() -> LoadHistoryIdResponse:
    """
    Load the previously saved Gmail history ID from file.
    
    This tool retrieves the history ID that was saved from a previous history check.
    It's useful for establishing a baseline for subsequent history checks.
    
    Returns:
        An object containing the history ID and any error messages.
    """
    try:
        logger.info("Loading saved history ID")
        
        # Use helper to load the history ID
        result = gmail_helper.load_history_id()
        
        if result["error"] and "No history ID file found" not in result["error"]:
            logger.error(result["error"])
        else:
            if result["history_id"]:
                logger.info(f"Successfully loaded history ID: {result['history_id']}")
            else:
                logger.info("No saved history ID found")
        
        return LoadHistoryIdResponse(
            history_id=result["history_id"],
            error=result["error"]
        )
        
    except Exception as e:
        error_msg = f"Error loading saved history ID: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return LoadHistoryIdResponse(
            history_id=None,
            error=error_msg
        )

@mcp.tool()
async def get_gmail_history(request: HistoryRequest) -> HistoryResponse:
    """
    Retrieve changes that have occurred in the mailbox since a specific point in time.
    
    This tool uses the Gmail API's users.history.list method to fetch a history of 
    changes to the user's mailbox, such as added/deleted messages and label changes.
    
    Args:
        request: An object containing:
            - start_history_id: The starting historyId to get changes from (optional)
            - history_types: List of history types to retrieve (optional, can include 
              messageAdded, messageDeleted, labelAdded, labelRemoved)
            - max_results: Maximum number of history records to return (optional, defaults to 100)
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the history records, latest history ID, and any error messages.
    """
    try:
        logger.info(f"Retrieving Gmail history for user: {request.user_id}")
        
        # Get history from helper
        result = gmail_helper.get_history(
            start_history_id=request.start_history_id,
            history_types=request.history_types,
            max_results=request.max_results,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return HistoryResponse(
                history_records=[],
                latest_history_id=None,
                error=result["error"]
            )
        
        # Process history records
        processed_history = []
        for record in result["history"]:
            processed_record = {
                'id': record.get('id'),
                'changes': []
            }
            
            # Check for messages added
            if 'messagesAdded' in record:
                for msg in record['messagesAdded']:
                    message = msg.get('message', {})
                    processed_record['changes'].append({
                        'type': 'messageAdded',
                        'message_id': message.get('id'),
                        'thread_id': message.get('threadId'),
                        'label_ids': message.get('labelIds', [])
                    })
            
            # Check for messages deleted
            if 'messagesDeleted' in record:
                for msg in record['messagesDeleted']:
                    message = msg.get('message', {})
                    processed_record['changes'].append({
                        'type': 'messageDeleted',
                        'message_id': message.get('id'),
                        'thread_id': message.get('threadId')
                    })
            
            # Check for label additions
            if 'labelsAdded' in record:
                for label in record['labelsAdded']:
                    message = label.get('message', {})
                    processed_record['changes'].append({
                        'type': 'labelAdded',
                        'message_id': message.get('id'),
                        'thread_id': message.get('threadId'),
                        'label_ids': label.get('labelIds', [])
                    })
            
            # Check for label removals
            if 'labelsRemoved' in record:
                for label in record['labelsRemoved']:
                    message = label.get('message', {})
                    processed_record['changes'].append({
                        'type': 'labelRemoved',
                        'message_id': message.get('id'),
                        'thread_id': message.get('threadId'),
                        'label_ids': label.get('labelIds', [])
                    })
            
            processed_history.append(processed_record)
        
        # Save the latest history ID for next time
        if result["latest_history_id"]:
            gmail_helper.save_history_id(result["latest_history_id"])
        
        logger.info(f"Successfully retrieved {len(processed_history)} history records")
        return HistoryResponse(
            history_records=processed_history,
            latest_history_id=result["latest_history_id"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_gmail_history: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return HistoryResponse(
            history_records=[],
            latest_history_id=None,
            error=error_msg
        )

# -------------------------------------------------------------------------
# Authentication Tool
# -------------------------------------------------------------------------

class AuthenticationRequest(BaseModel):
    pass  # No parameters needed

class AuthenticationResponse(BaseModel):
    authenticated: bool
    message: str
    email: Optional[str] = None
    error: Optional[str] = None

@mcp.tool()
async def authenticate_gmail(request: AuthenticationRequest) -> AuthenticationResponse:
    """
    Authenticate with Gmail API and establish a connection.
    
    This tool initiates the OAuth flow if needed and validates the connection.
    For new users, it will open a browser window for authentication.
    For returning users with valid credentials, it will use the stored token.
    
    Returns:
        An object containing authentication status and any error messages.
    """
    try:
        logger.info("Manual authentication requested")
        
        # Try to authenticate using helper function
        auth_result = ensure_authenticated()
        
        if auth_result["authenticated"]:
            logger.info(f"Manual authentication successful: {auth_result['message']}")
            return AuthenticationResponse(
                authenticated=True,
                message=auth_result['message'],
                email=auth_result.get('email'),
                error=None
            )
        else:
            logger.error(f"Manual authentication failed: {auth_result['message']}")
            return AuthenticationResponse(
                authenticated=False,
                message=auth_result['message'],
                error=auth_result['error']
            )
        
    except Exception as e:
        error_msg = f"Error in authenticate_gmail: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return AuthenticationResponse(
            authenticated=False,
            message="Unexpected error during authentication",
            error=error_msg
        )

# -------------------------------------------------------------------------
# Message Operations
# -------------------------------------------------------------------------

class SendMessageRequest(BaseModel):
    to: str
    subject: str
    message_text: str
    html_content: Optional[str] = None
    user_id: Optional[str] = 'me'

class MessageResponse(BaseModel):
    message: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def send_gmail_message(request: SendMessageRequest) -> MessageResponse:
    """
    Send a new email message.
    
    This tool creates and sends a new email message directly, without saving it as a draft first.
    
    Args:
        request: An object containing:
            - to: Email recipient(s)
            - subject: Email subject
            - message_text: Email body as plain text
            - html_content: Optional HTML version of the email body
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the sent message data and any error messages.
    """
    try:
        logger.info(f"Sending email to: {request.to}")
        
        # Get user's email for the 'from' field
        profile_result = gmail_helper.get_profile(user_id=request.user_id)
        if profile_result["error"]:
            return MessageResponse(
                message=None,
                error=f"Failed to get user profile: {profile_result['error']}"
            )
        
        sender = profile_result["profile"]["emailAddress"]
        
        # Create message body
        message_body = gmail_helper.create_message(
            sender=sender,
            to=request.to,
            subject=request.subject,
            message_text=request.message_text
        )
        
        if request.html_content:
            # If HTML content is provided, we need to create a multipart message
            message_body = {
                'raw': gmail_helper.create_multipart_message(
                    sender=sender,
                    to=request.to,
                    subject=request.subject,
                    message_text=request.message_text,
                    html_content=request.html_content
                )
            }
        
        # Send message
        result = gmail_helper.send_message(
            message_body=message_body,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return MessageResponse(
                message=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully sent email with ID: {result['message']['id']}")
        return MessageResponse(
            message=result["message"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in send_gmail_message: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return MessageResponse(message=None, error=error_msg)

class ModifyMessageRequest(BaseModel):
    message_id: str
    add_labels: Optional[List[str]] = None
    remove_labels: Optional[List[str]] = None
    user_id: Optional[str] = 'me'

@mcp.tool()
async def modify_gmail_message(request: ModifyMessageRequest) -> MessageResponse:
    """
    Modify the labels of an existing email message.
    
    This tool updates the labels applied to a message, which can change its
    status (e.g., read/unread, starred, important) or move it between folders.
    
    Args:
        request: An object containing:
            - message_id: ID of the message to modify
            - add_labels: List of label IDs to add (optional)
            - remove_labels: List of label IDs to remove (optional)
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the modified message data and any error messages.
    """
    try:
        logger.info(f"Modifying message with ID: {request.message_id}")
        
        if not request.add_labels and not request.remove_labels:
            return MessageResponse(
                message=None,
                error="At least one of add_labels or remove_labels must be provided"
            )
        
        # Modify the message
        result = gmail_helper.modify_message(
            message_id=request.message_id,
            add_labels=request.add_labels,
            remove_labels=request.remove_labels,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return MessageResponse(
                message=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully modified message {request.message_id}")
        return MessageResponse(
            message=result["message"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in modify_gmail_message: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return MessageResponse(message=None, error=error_msg)

# -------------------------------------------------------------------------
# Thread Management Tools
# -------------------------------------------------------------------------

class ThreadRequest(BaseModel):
    query: Optional[str] = ""
    max_results: Optional[int] = 10
    user_id: Optional[str] = 'me'

class ThreadListResponse(BaseModel):
    threads: List[Dict[str, Any]]
    error: Optional[str] = None

@mcp.tool()
async def list_gmail_threads(request: ThreadRequest) -> ThreadListResponse:
    """
    List Gmail conversation threads based on the provided query.
    
    Threads are groups of related messages that form a conversation. This tool
    returns a list of thread IDs and metadata that match the search query.
    
    Args:
        request: An object containing:
            - query: Gmail search query (optional, same format as Gmail search box)
            - max_results: Maximum number of threads to return (optional, defaults to 10)
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the list of threads and any error messages.
    """
    try:
        logger.info(f"Listing Gmail threads with query: {request.query}")
        
        # Use helper to get threads
        result = gmail_helper.list_threads(
            query=request.query,
            max_results=request.max_results,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return ThreadListResponse(
                threads=[],
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved {len(result['threads'])} threads")
        return ThreadListResponse(
            threads=result["threads"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in list_gmail_threads: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ThreadListResponse(threads=[], error=error_msg)

class GetThreadRequest(BaseModel):
    thread_id: str
    user_id: Optional[str] = 'me'
    format: Optional[str] = 'metadata'

class ThreadResponse(BaseModel):
    thread: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def get_gmail_thread(request: GetThreadRequest) -> ThreadResponse:
    """
    Retrieve a specific conversation thread with all its messages.
    
    This tool fetches a thread by its ID, including all messages in the
    conversation with their metadata. The 'metadata' format provides headers like
    From, To, Subject, and Date, plus message snippets, which is sufficient for
    most use cases.
    
    Note: Using format='full' requires additional permissions beyond the default
    Gmail API scopes and may fail with a permission error.
    
    Args:
        request: An object containing:
            - thread_id: ID of the thread to retrieve
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
            - format: Format of the messages (optional, defaults to 'metadata')
        
    Returns:
        An object containing the thread data and any error messages.
    """
    try:
        logger.info(f"Retrieving Gmail thread with ID: {request.thread_id}")
        
        # Use helper to get thread
        result = gmail_helper.get_thread(
            thread_id=request.thread_id,
            user_id=request.user_id,
            format=request.format
        )
        
        if result["error"]:
            logger.error(result["error"])
            return ThreadResponse(
                thread=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved thread with {len(result['thread'].get('messages', []))} messages")
        return ThreadResponse(
            thread=result["thread"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_gmail_thread: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ThreadResponse(thread=None, error=error_msg)

# -------------------------------------------------------------------------
# Label Management Tools
# -------------------------------------------------------------------------

class ListLabelsRequest(BaseModel):
    user_id: Optional[str] = 'me'

class LabelsResponse(BaseModel):
    labels: List[Dict[str, Any]]
    error: Optional[str] = None

@mcp.tool()
async def list_gmail_labels(request: ListLabelsRequest) -> LabelsResponse:
    """
    List all labels in the user's Gmail account.
    
    This tool retrieves all labels from the user's Gmail account, including both
    system labels (INBOX, SENT, DRAFT, etc.) and user-created labels. Labels are
    used to categorize and organize emails in Gmail.
    
    Args:
        request: An object containing:
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the list of labels and any error messages.
    """
    try:
        logger.info(f"Listing Gmail labels for user: {request.user_id}")
        
        # Use helper to get labels
        result = gmail_helper.list_labels(user_id=request.user_id)
        
        if result["error"]:
            logger.error(result["error"])
            return LabelsResponse(
                labels=[],
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved {len(result['labels'])} labels")
        return LabelsResponse(
            labels=result["labels"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in list_gmail_labels: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return LabelsResponse(labels=[], error=error_msg)

class CreateLabelRequest(BaseModel):
    name: str
    text_color: Optional[str] = None
    background_color: Optional[str] = None
    user_id: Optional[str] = 'me'

class LabelResponse(BaseModel):
    label: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def create_gmail_label(request: CreateLabelRequest) -> LabelResponse:
    """
    Create a new label in the user's Gmail account.
    
    This tool creates a new custom label that can be applied to emails for
    organization purposes. You can specify colors for the label to make it
    visually distinct.
    
    Args:
        request: An object containing:
            - name: Display name for the label (required)
            - text_color: Text color in hex format (e.g., '#000000') (optional)
            - background_color: Background color in hex format (e.g., '#ffffff') (optional)
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the created label data and any error messages.
    """
    try:
        logger.info(f"Creating Gmail label '{request.name}' for user: {request.user_id}")
        
        # Use helper to create label
        result = gmail_helper.create_label(
            name=request.name,
            text_color=request.text_color,
            background_color=request.background_color,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return LabelResponse(
                label=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully created label '{request.name}' with ID: {result['label'].get('id')}")
        return LabelResponse(
            label=result["label"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in create_gmail_label: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return LabelResponse(label=None, error=error_msg)

class UpdateLabelRequest(BaseModel):
    label_id: str
    name: Optional[str] = None
    text_color: Optional[str] = None
    background_color: Optional[str] = None
    message_list_visibility: Optional[str] = None
    label_list_visibility: Optional[str] = None
    user_id: Optional[str] = 'me'

@mcp.tool()
async def update_gmail_label(request: UpdateLabelRequest) -> LabelResponse:
    """
    Update an existing label in the user's Gmail account.
    
    This tool modifies properties of an existing label such as its name, colors,
    or visibility settings.
    
    Args:
        request: An object containing:
            - label_id: ID of the label to update (required)
            - name: New display name for the label (optional)
            - text_color: New text color in hex format (optional)
            - background_color: New background color in hex format (optional)
            - message_list_visibility: Visibility in message list ('show' or 'hide') (optional)
            - label_list_visibility: Visibility in label list ('labelShow', 'labelHide', 'labelShowIfUnread') (optional)
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the updated label data and any error messages.
    """
    try:
        logger.info(f"Updating Gmail label {request.label_id} for user: {request.user_id}")
        
        # First get the existing label to update only specified fields
        existing_label_result = gmail_helper.list_labels(user_id=request.user_id)
        
        if existing_label_result["error"]:
            return LabelResponse(
                label=None,
                error=f"Failed to retrieve existing label: {existing_label_result['error']}"
            )
        
        # Find the label to update
        target_label = None
        for label in existing_label_result["labels"]:
            if label.get('id') == request.label_id:
                target_label = label
                break
        
        if not target_label:
            return LabelResponse(
                label=None,
                error=f"Label with ID {request.label_id} not found"
            )
        
        # Create updated label body with only the fields to change
        updated_label = {}
        
        if request.name is not None:
            updated_label['name'] = request.name
        else:
            updated_label['name'] = target_label.get('name')
            
        if request.message_list_visibility is not None:
            updated_label['messageListVisibility'] = request.message_list_visibility
        else:
            updated_label['messageListVisibility'] = target_label.get('messageListVisibility')
            
        if request.label_list_visibility is not None:
            updated_label['labelListVisibility'] = request.label_list_visibility
        else:
            updated_label['labelListVisibility'] = target_label.get('labelListVisibility')
        
        # Update color if either text_color or background_color is provided
        if request.text_color is not None or request.background_color is not None:
            text_color = request.text_color
            if text_color is None and 'color' in target_label:
                text_color = target_label['color'].get('textColor')
                
            background_color = request.background_color
            if background_color is None and 'color' in target_label:
                background_color = target_label['color'].get('backgroundColor')
                
            if text_color and background_color:
                updated_label['color'] = {
                    'textColor': text_color,
                    'backgroundColor': background_color
                }
        
        # Use helper to update label
        result = gmail_helper.update_label(
            label_id=request.label_id,
            updated_label=updated_label,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return LabelResponse(
                label=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully updated label {request.label_id}")
        return LabelResponse(
            label=result["label"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in update_gmail_label: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return LabelResponse(label=None, error=error_msg)

# -------------------------------------------------------------------------
# Filter Management Tools
# -------------------------------------------------------------------------

class ListFiltersRequest(BaseModel):
    user_id: Optional[str] = 'me'

class FiltersResponse(BaseModel):
    filters: List[Dict[str, Any]]
    error: Optional[str] = None

@mcp.tool()
async def list_gmail_filters(request: ListFiltersRequest) -> FiltersResponse:
    """
    List all email filters in the user's Gmail account.
    
    This tool retrieves all filters that have been set up in the user's Gmail
    account. Filters automatically process incoming emails based on criteria
    such as sender, recipient, subject, or content.
    
    Args:
        request: An object containing:
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the list of filters and any error messages.
    """
    try:
        logger.info(f"Listing Gmail filters for user: {request.user_id}")
        
        # Use helper to get filters
        result = gmail_helper.list_filters(user_id=request.user_id)
        
        if result["error"]:
            logger.error(result["error"])
            return FiltersResponse(
                filters=[],
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved {len(result['filters'])} filters")
        return FiltersResponse(
            filters=result["filters"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in list_gmail_filters: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return FiltersResponse(filters=[], error=error_msg)

class FilterCriteria(BaseModel):
    from_: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None
    subject: Optional[str] = None
    query: Optional[str] = None
    has_attachment: Optional[bool] = None
    exclude_chats: Optional[bool] = None
    size: Optional[int] = None
    size_comparison: Optional[str] = None

class FilterAction(BaseModel):
    add_label_ids: Optional[List[str]] = None
    remove_label_ids: Optional[List[str]] = None
    forward: Optional[str] = None

class CreateFilterRequest(BaseModel):
    criteria: FilterCriteria
    action: FilterAction
    user_id: Optional[str] = 'me'

class FilterResponse(BaseModel):
    filter: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def create_gmail_filter(request: CreateFilterRequest) -> FilterResponse:
    """
    Create a new email filter in the user's Gmail account.
    
    This tool creates a new filter that automatically processes incoming emails
    based on specified criteria. When emails match the criteria, the specified
    actions are applied (like adding labels, marking as read, etc.).
    
    Args:
        request: An object containing:
            - criteria: Filter matching criteria object with fields:
                - from: Sender email address
                - to: Recipient email address
                - subject: Email subject text
                - query: Gmail search query
                - has_attachment: Whether the email has attachments
                - exclude_chats: Whether to exclude chats
                - size: Size in bytes
                - size_comparison: Size comparison type ('larger' or 'smaller')
            - action: Actions to take on matching emails:
                - add_label_ids: List of label IDs to add
                - remove_label_ids: List of label IDs to remove
                - forward: Email address to forward to
            - user_id: User ID (optional, defaults to 'me' for authenticated user)
        
    Returns:
        An object containing the created filter data and any error messages.
    """
    try:
        logger.info(f"Creating Gmail filter for user: {request.user_id}")
        
        # Convert pydantic models to dictionaries for the API
        # Handle the 'from_' field special case
        criteria_dict = request.criteria.dict(by_alias=False, exclude_none=True)
        if 'from_' in criteria_dict:
            criteria_dict['from'] = criteria_dict.pop('from_')
            
        action_dict = request.action.dict(exclude_none=True)
        
        # Use helper to create filter
        result = gmail_helper.create_filter(
            criteria=criteria_dict,
            action=action_dict,
            user_id=request.user_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return FilterResponse(
                filter=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully created filter with ID: {result['filter'].get('id')}")
        return FilterResponse(
            filter=result["filter"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in create_gmail_filter: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return FilterResponse(filter=None, error=error_msg)

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

    # Get MCP server instance from FastMCP
    mcp_server = mcp._mcp_server

    parser = argparse.ArgumentParser(description="Gmail MCP Server")
    parser.add_argument("--port", type=int, default=GMAIL_MCP_PORT, help="Port for server")
    parser.add_argument("--host", type=str, default=MCP_HOST, help="Host for server")
    parser.add_argument("--skip-auth-check", action="store_true", help="Skip authentication check before starting server")
    
    args = parser.parse_args()
    
    # Check authentication before starting the server
    if not args.skip_auth_check:
        logger.info("Checking Gmail API authentication before starting server")
        
        auth_result = ensure_authenticated()
        
        if auth_result["authenticated"]:
            logger.info(f"Authentication successful: {auth_result['message']}")
        else:
            logger.error(f"Authentication failed: {auth_result['message']}")
            logger.error(f"Error details: {auth_result['error']}")
            
            # Print a user-friendly message
            print("\n" + "="*80)
            print(" AUTHENTICATION ERROR ".center(80, "="))
            print("="*80)
            print(f"\nFailed to authenticate with Gmail API: {auth_result['message']}")
            print("\nThe server will still start, but Gmail-related operations may fail.")
            print("You can try accessing the server and authenticating through API requests.")
            print("\nTo bypass this check next time, use --skip-auth-check\n")
    
    logger.info(f"Starting Gmail MCP Server on {args.host}:{args.port}")
    
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
