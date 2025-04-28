#!/usr/bin/env python
"""
Helper functions for Gmail MCP tools
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request as GoogleRequest
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger('gmail_helper')

class GmailHelper:
    """Helper class for Gmail operations"""
    
    def __init__(self, scopes: List[str], token_path: Path, credentials_path: Path):
        """Initialize Gmail helper.
        
        Args:
            scopes: List of Gmail API scopes
            token_path: Path to token.json
            credentials_path: Path to credentials.json
        """
        self.scopes = scopes
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.service = None
    
    def authenticate(self) -> bool:
        """Authenticate with Gmail API.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            creds = None
            # Load existing credentials if available
            if self.token_path.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)
                    logger.info("Using existing credentials from token file")
                except Exception as e:
                    logger.error(f"Error loading credentials: {e}")
                    return False

            # Handle credential refresh or new authentication
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        logger.info("Refreshing expired credentials")
                        creds.refresh(GoogleRequest())
                    except Exception as e:
                        logger.error(f"Error refreshing credentials: {e}")
                        # If refresh fails, we'll need to re-authenticate
                        creds = None
                
                # If still no valid credentials, start new authentication flow
                if not creds or not creds.valid:
                    try:
                        logger.info("No valid credentials found. Starting new authentication flow.")
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(self.credentials_path), self.scopes)
                        
                        # Print clear instructions for the user
                        print("\n" + "="*80)
                        print(" GMAIL AUTHENTICATION REQUIRED ".center(80, "="))
                        print("="*80)
                        print("\nThis application needs to access your Gmail account.")
                        print("1. A browser window will open shortly.")
                        print("2. Select your Gmail account and grant the requested permissions.")
                        print("3. After authorization, you'll be redirected to a local page.")
                        print("\nIf no browser opens automatically, use the URL that will be displayed.\n")
                        
                        # Add access_type='offline' to get a refresh token
                        creds = flow.run_local_server(
                            port=8080, 
                            access_type='offline',
                            prompt='consent',  # Force prompt to ensure refresh token is provided
                            success_message="Authentication complete! You can close this window and return to the application."
                        )
                        
                        print("\n" + "="*80)
                        print(" AUTHENTICATION SUCCESSFUL ".center(80, "="))
                        print("="*80 + "\n")
                        
                    except Exception as e:
                        logger.error(f"Error in OAuth flow: {e}")
                        return False

                # Save credentials
                try:
                    logger.info("Saving new credentials to token file")
                    with open(self.token_path, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logger.error(f"Error saving credentials: {e}")
                    return False

            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=creds)
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def list_messages(self, query: str = "", max_results: int = 10) -> Dict[str, Any]:
        """List Gmail messages.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results to return
            
        Returns:
            Dict containing messages and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "messages": [],
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            # Get message list
            response = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = response.get('messages', [])
            if not messages:
                return {
                    "messages": [],
                    "error": f"No messages found matching query: {query}"
                }
            
            # Process messages
            processed_messages = []
            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='metadata',
                        metadataHeaders=['Subject', 'From', 'Date']
                    ).execute()
                    
                    # Extract headers
                    headers = {}
                    for header in msg['payload']['headers']:
                        if header['name'] in ['Subject', 'From', 'Date']:
                            headers[header['name']] = header['value']
                    
                    processed_messages.append({
                        'id': message['id'],
                        'headers': headers,
                        'snippet': msg.get('snippet', '')
                    })
                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {e}")
                    continue
            
            if not processed_messages:
                return {
                    "messages": [],
                    "error": "No messages could be processed successfully"
                }
            
            return {
                "messages": processed_messages,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error listing messages: {e}")
            return {
                "messages": [],
                "error": f"Error listing messages: {str(e)}"
            }
    
    def get_message_details(self, message_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific message.
        
        Args:
            message_id: ID of the message to retrieve
            
        Returns:
            Dict containing message details and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "message": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return {
                "message": message,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error getting message details: {e}")
            return {
                "message": None,
                "error": f"Error getting message details: {str(e)}"
            }
    
    def get_profile(self, user_id: str = 'me') -> Dict[str, Any]:
        """Gets the user's Gmail profile information.
        
        Args:
            user_id: The user's email address or 'me' for the authenticated user
            
        Returns:
            Dict containing profile data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "profile": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Retrieving profile for user {user_id}")
            profile = self.service.users().getProfile(userId=user_id).execute()
            logger.info(f"Retrieved profile for {profile.get('emailAddress')}")
            
            return {
                "profile": profile,
                "error": None
            }
        except Exception as e:
            error_msg = f"Error retrieving profile: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "profile": None,
                "error": error_msg
            }
    
    def setup_watch(self, topic_name: str, label_ids: List[str] = None, user_id: str = 'me') -> Dict[str, Any]:
        """Sets up push notifications for mailbox changes.
        
        Args:
            topic_name: Google Cloud Pub/Sub topic
            label_ids: List of label IDs to watch (default: ['INBOX'])
            user_id: The user's email address or 'me' for the authenticated user
            
        Returns:
            Dict containing watch data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "watch_data": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        if label_ids is None:
            label_ids = ['INBOX']
            
        try:
            logger.debug(f"Setting up watch for user {user_id} on topic {topic_name}")
            request = {
                'topicName': topic_name,
                'labelIds': label_ids
            }
            response = self.service.users().watch(userId=user_id, body=request).execute()
            logger.info(f"Watch setup successful. Expires: {response.get('expiration')}")
            
            return {
                "watch_data": response,
                "error": None
            }
        except Exception as e:
            error_msg = f"Error setting up watch: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "watch_data": None,
                "error": error_msg
            }
    
    # -------------------------------------------------------------------------
    # Draft Management Methods
    # -------------------------------------------------------------------------
    
    def create_message(self, sender: str, to: str, subject: str, message_text: str) -> Dict[str, str]:
        """Create a message for an email.
        
        Args:
            sender: Email sender
            to: Email recipient(s)
            subject: Email subject
            message_text: Email body
            
        Returns:
            Dict with the 'raw' email message
        """
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    
    def create_multipart_message(self, sender: str, to: str, subject: str, 
                              message_text: str, html_content: str) -> str:
        """Create a multipart message with both plain text and HTML content.
        
        Args:
            sender: Email sender
            to: Email recipient(s)
            subject: Email subject
            message_text: Email body as plain text
            html_content: Email body as HTML
            
        Returns:
            Base64url encoded email message
        """
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        
        # Create the plain text and HTML parts
        text_part = MIMEText(message_text, 'plain')
        html_part = MIMEText(html_content, 'html')
        
        # Attach parts
        message.attach(text_part)
        message.attach(html_part)
        
        # Encode as base64url
        return base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    def create_draft(self, message_body: Dict[str, Any], user_id: str = 'me') -> Dict[str, Any]:
        """Create a draft email.
        
        Args:
            message_body: Dict containing the message to create
            user_id: User's email address or 'me'
            
        Returns:
            Dict with draft data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "draft": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Creating draft for user {user_id}")
            draft = {'message': message_body}
            draft = self.service.users().drafts().create(userId=user_id, body=draft).execute()
            logger.info(f"Draft created with ID: {draft['id']}")
            return {
                "draft": draft,
                "error": None
            }
        except HttpError as error:
            error_msg = f"Error creating draft: {str(error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "draft": None,
                "error": error_msg
            }
    
    def delete_draft(self, draft_id: str, user_id: str = 'me') -> Dict[str, Any]:
        """Delete a draft email.
        
        Args:
            draft_id: ID of the draft to delete
            user_id: User's email address or 'me'
            
        Returns:
            Dict with success status and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "success": False,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Deleting draft {draft_id} for user {user_id}")
            self.service.users().drafts().delete(userId=user_id, id=draft_id).execute()
            logger.info(f"Draft {draft_id} deleted successfully")
            return {
                "success": True,
                "error": None
            }
        except HttpError as error:
            error_msg = f"Error deleting draft: {str(error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_draft(self, draft_id: str, user_id: str = 'me', format: str = 'full') -> Dict[str, Any]:
        """Get a specific draft.
        
        Args:
            draft_id: ID of the draft to retrieve
            user_id: User's email address or 'me'
            format: Format of the message (minimal, full, raw, metadata)
            
        Returns:
            Dict with draft data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "draft": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Retrieving draft {draft_id} for user {user_id}")
            draft = self.service.users().drafts().get(userId=user_id, id=draft_id, format=format).execute()
            logger.info(f"Retrieved draft {draft_id}")
            return {
                "draft": draft,
                "error": None
            }
        except HttpError as error:
            error_msg = f"Error retrieving draft: {str(error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "draft": None,
                "error": error_msg
            }
    
    def list_drafts(self, user_id: str = 'me', max_results: int = 10) -> Dict[str, Any]:
        """List all drafts.
        
        Args:
            user_id: User's email address or 'me'
            max_results: Maximum number of drafts to return
            
        Returns:
            Dict with list of drafts and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "drafts": [],
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Listing drafts for user {user_id}")
            response = self.service.users().drafts().list(userId=user_id, maxResults=max_results).execute()
            drafts = response.get('drafts', [])
            logger.info(f"Found {len(drafts)} drafts")
            
            # Get full draft details for each draft
            detailed_drafts = []
            for draft in drafts:
                try:
                    draft_detail = self.service.users().drafts().get(
                        userId=user_id, 
                        id=draft['id'],
                        format='metadata'
                    ).execute()
                    detailed_drafts.append(draft_detail)
                except Exception as e:
                    logger.error(f"Error processing draft {draft['id']}: {e}")
                    continue
            
            return {
                "drafts": detailed_drafts,
                "error": None
            }
        except HttpError as error:
            error_msg = f"Error listing drafts: {str(error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "drafts": [],
                "error": error_msg
            }
    
    def send_draft(self, draft_id: str, user_id: str = 'me') -> Dict[str, Any]:
        """Send an existing draft.
        
        Args:
            draft_id: ID of the draft to send
            user_id: User's email address or 'me'
            
        Returns:
            Dict with sent message data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "message": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Sending draft {draft_id} for user {user_id}")
            message = self.service.users().drafts().send(userId=user_id, body={'id': draft_id}).execute()
            logger.info(f"Draft {draft_id} sent successfully. Message ID: {message['id']}")
            return {
                "message": message,
                "error": None
            }
        except HttpError as error:
            error_msg = f"Error sending draft: {str(error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "message": None,
                "error": error_msg
            }
    
    def update_draft(self, draft_id: str, message_body: Dict[str, Any], user_id: str = 'me') -> Dict[str, Any]:
        """Update an existing draft.
        
        Args:
            draft_id: ID of the draft to update
            message_body: New message body to replace the existing draft
            user_id: User's email address or 'me'
            
        Returns:
            Dict with updated draft data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "draft": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Updating draft {draft_id} for user {user_id}")
            draft = {'message': message_body, 'id': draft_id}
            updated_draft = self.service.users().drafts().update(userId=user_id, id=draft_id, body=draft).execute()
            logger.info(f"Draft {draft_id} updated successfully")
            return {
                "draft": updated_draft,
                "error": None
            }
        except HttpError as error:
            error_msg = f"Error updating draft: {str(error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "draft": None,
                "error": error_msg
            }
    
    def save_history_id(self, history_id: str, file_path: str = 'gmail_mcp_tool/last_history_id.txt') -> Dict[str, Any]:
        """Save the historyId to a file for future reference.
        
        Args:
            history_id: The historyId to save.
            file_path: Path to the file to save the historyId.
            
        Returns:
            Dict containing success status and any error
        """
        try:
            logger.debug(f"Saving historyId {history_id} to {file_path}")
            with open(file_path, 'w') as f:
                f.write(str(history_id))
            logger.debug(f"Saved historyId {history_id} to {file_path}")
            return {
                "success": True,
                "error": None
            }
        except Exception as e:
            error_msg = f"Error saving historyId: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def load_history_id(self, file_path: str = 'gmail_mcp_tool/last_history_id.txt') -> Dict[str, Any]:
        """Load the historyId from a file.
        
        Args:
            file_path: Path to the file containing the historyId.
            
        Returns:
            Dict containing historyId and any error
        """
        try:
            if Path(file_path).exists():
                with open(file_path, 'r') as f:
                    history_id = f.read().strip()
                logger.debug(f"Loaded historyId {history_id} from {file_path}")
                return {
                    "history_id": history_id,
                    "error": None
                }
            else:
                logger.debug(f"No saved historyId found at {file_path}")
                return {
                    "history_id": None,
                    "error": f"No history ID file found at {file_path}"
                }
        except Exception as e:
            error_msg = f"Error loading historyId: {str(e)}"
            logger.error(error_msg)
            return {
                "history_id": None,
                "error": error_msg
            }
            
    def get_history(self, start_history_id: str = None, history_types: List[str] = None, 
                   max_results: int = 100, user_id: str = 'me') -> Dict[str, Any]:
        """Retrieve a history record of changes to the user's mailbox.
        
        Args:
            start_history_id: The starting historyId value to get changes from.
            history_types: List of history types to retrieve (messageAdded, messageDeleted, labelAdded, labelRemoved).
            max_results: Maximum number of history records to return.
            user_id: User's email address or 'me'.
            
        Returns:
            Dict with history records, latest historyId and any error.
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "history": [],
                    "latest_history_id": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        # If no start_history_id, get the latest one
        if not start_history_id:
            try:
                profile = self.service.users().getProfile(userId=user_id).execute()
                latest_id = profile.get('historyId')
                logger.info(f"No starting historyId provided, using current historyId: {latest_id}")
                
                # Return the latest ID but no records since we're just establishing a baseline
                return {
                    "history": [],
                    "latest_history_id": latest_id,
                    "error": None
                }
            except Exception as e:
                error_msg = f"Error getting latest historyId: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {
                    "history": [],
                    "latest_history_id": None,
                    "error": error_msg
                }
        
        try:
            logger.debug(f"Retrieving history for user {user_id} starting from history ID: {start_history_id}")
            
            # Prepare parameters
            params = {
                'userId': user_id,
                'maxResults': max_results,
                'startHistoryId': start_history_id
            }
            
            # Add history_types if provided
            if history_types:
                params['historyTypes'] = history_types
            
            # Execute the API call
            response = self.service.users().history().list(**params).execute()
            
            # Extract history records
            history = response.get('history', [])
            next_page_token = response.get('nextPageToken')
            
            # Handle pagination if there are more results
            while next_page_token:
                logger.debug(f"Fetching next page of history with token: {next_page_token}")
                params['pageToken'] = next_page_token
                response = self.service.users().history().list(**params).execute()
                history.extend(response.get('history', []))
                next_page_token = response.get('nextPageToken')
            
            # Get latest historyId
            latest_id = history[-1]['id'] if history else start_history_id
            
            logger.info(f"Retrieved {len(history)} history records")
            return {
                "history": history,
                "latest_history_id": latest_id,
                "error": None
            }
        
        except Exception as e:
            error_msg = f"Error retrieving history: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "history": [],
                "latest_history_id": None,
                "error": error_msg
            }

    # -------------------------------------------------------------------------
    # Message Operations
    # -------------------------------------------------------------------------
    
    def modify_message(self, message_id: str, add_labels: List[str] = None, 
                      remove_labels: List[str] = None, user_id: str = 'me') -> Dict[str, Any]:
        """Modify the labels of a message.
        
        Args:
            message_id: ID of the message to modify.
            add_labels: List of label IDs to add.
            remove_labels: List of label IDs to remove.
            user_id: User's email address or 'me'.
            
        Returns:
            Dict with modified message data and any error.
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "message": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Modifying message {message_id} for user {user_id}")
            
            # Create the label modification request
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels
                
            # Execute the API call
            modified_message = self.service.users().messages().modify(
                userId=user_id, 
                id=message_id, 
                body=body
            ).execute()
            
            logger.info(f"Message {message_id} modified successfully")
            return {
                "message": modified_message,
                "error": None
            }
        except HttpError as error:
            error_msg = f"Error modifying message: {str(error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "message": None,
                "error": error_msg
            }

    def send_message(self, message_body: Dict[str, Any], user_id: str = 'me') -> Dict[str, Any]:
        """Send an email message.
        
        Args:
            message_body: Dict containing the message to send (with 'raw' field).
            user_id: User's email address or 'me'.
            
        Returns:
            Dict with sent message data and any error.
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "message": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Sending message for user {user_id}")
            sent_message = self.service.users().messages().send(
                userId=user_id, 
                body=message_body
            ).execute()
            logger.info(f"Message sent successfully. Message ID: {sent_message['id']}")
            return {
                "message": sent_message,
                "error": None
            }
        except HttpError as error:
            error_msg = f"Error sending message: {str(error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "message": None,
                "error": error_msg
            }

    # -------------------------------------------------------------------------
    # Thread Operations
    # -------------------------------------------------------------------------
    
    def list_threads(self, query: str = "", max_results: int = 10, user_id: str = 'me') -> Dict[str, Any]:
        """List Gmail threads.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results to return
            user_id: User's email address or 'me'
            
        Returns:
            Dict containing threads and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "threads": [],
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Listing threads for user {user_id} with query: {query}")
            
            # Get thread list
            response = self.service.users().threads().list(
                userId=user_id,
                q=query,
                maxResults=max_results
            ).execute()
            
            threads = response.get('threads', [])
            if not threads:
                return {
                    "threads": [],
                    "error": f"No threads found matching query: {query}"
                }
            
            logger.info(f"Found {len(threads)} threads matching query")
            return {
                "threads": threads,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error listing threads: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "threads": [],
                "error": error_msg
            }
    
    def get_thread(self, thread_id: str, user_id: str = 'me', format: str = 'metadata') -> Dict[str, Any]:
        """Get detailed information about a specific thread.
        
        Args:
            thread_id: ID of the thread to retrieve
            user_id: User's email address or 'me'
            format: Format of the thread messages (metadata, minimal, full)
                   Note: 'full' requires more permissions than 'metadata'
            
        Returns:
            Dict containing thread details and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "thread": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Getting thread {thread_id} for user {user_id} with format: {format}")
            
            # Handle potential permission issues with format
            try:
                thread = self.service.users().threads().get(
                    userId=user_id,
                    id=thread_id,
                    format=format
                ).execute()
            except HttpError as error:
                # If we get a permission error with 'full' format, try with 'metadata'
                if format == 'full' and "Metadata scope doesn't allow format FULL" in str(error):
                    logger.warning("Permission denied for 'full' format, falling back to 'metadata'")
                    thread = self.service.users().threads().get(
                        userId=user_id,
                        id=thread_id,
                        format='metadata'
                    ).execute()
                else:
                    # If it's a different error, re-raise it
                    raise
            
            logger.info(f"Successfully retrieved thread {thread_id} with {len(thread.get('messages', []))} messages")
            
            # Process the thread to extract useful information
            processed_thread = {
                'id': thread.get('id'),
                'historyId': thread.get('historyId'),
                'messages': []
            }
            
            # Process each message in the thread
            for message in thread.get('messages', []):
                processed_message = {
                    'id': message.get('id'),
                    'threadId': message.get('threadId'),
                    'labelIds': message.get('labelIds', []),
                    'snippet': message.get('snippet', ''),
                    'headers': {}
                }
                
                # Extract headers
                if 'payload' in message and 'headers' in message['payload']:
                    for header in message['payload']['headers']:
                        if header['name'] in ['Subject', 'From', 'To', 'Date']:
                            processed_message['headers'][header['name']] = header['value']
                
                processed_thread['messages'].append(processed_message)
            
            return {
                "thread": processed_thread,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error getting thread details: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "thread": None,
                "error": error_msg
            }

    # -------------------------------------------------------------------------
    # Label Operations
    # -------------------------------------------------------------------------
    
    def list_labels(self, user_id: str = 'me') -> Dict[str, Any]:
        """List all labels in the user's mailbox.
        
        Args:
            user_id: User's email address or 'me'
            
        Returns:
            Dict containing labels and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "labels": [],
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Listing labels for user {user_id}")
            
            # Get label list
            response = self.service.users().labels().list(userId=user_id).execute()
            
            labels = response.get('labels', [])
            logger.info(f"Found {len(labels)} labels")
            
            return {
                "labels": labels,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error listing labels: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "labels": [],
                "error": error_msg
            }
    
    def create_label(self, name: str, user_id: str = 'me', 
                    text_color: str = None, background_color: str = None) -> Dict[str, Any]:
        """Create a new label in the user's mailbox.
        
        Args:
            name: The display name of the label
            user_id: User's email address or 'me'
            text_color: Text color in hex format (e.g., '#000000')
            background_color: Background color in hex format (e.g., '#ffffff')
            
        Returns:
            Dict containing created label data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "label": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Creating label '{name}' for user {user_id}")
            
            # Create label body
            label_body = {
                'name': name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            # Add color if provided
            if text_color and background_color:
                label_body['color'] = {
                    'textColor': text_color,
                    'backgroundColor': background_color
                }
            
            # Create the label
            created_label = self.service.users().labels().create(
                userId=user_id,
                body=label_body
            ).execute()
            
            logger.info(f"Label '{name}' created successfully with ID: {created_label.get('id')}")
            
            return {
                "label": created_label,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error creating label: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "label": None,
                "error": error_msg
            }
    
    def update_label(self, label_id: str, updated_label: Dict[str, Any], 
                     user_id: str = 'me') -> Dict[str, Any]:
        """Update an existing label.
        
        Args:
            label_id: ID of the label to update
            updated_label: Dictionary with updated label properties
            user_id: User's email address or 'me'
            
        Returns:
            Dict containing updated label data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "label": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Updating label {label_id} for user {user_id}")
            
            # Update the label
            updated = self.service.users().labels().update(
                userId=user_id,
                id=label_id,
                body=updated_label
            ).execute()
            
            logger.info(f"Label {label_id} updated successfully")
            
            return {
                "label": updated,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error updating label: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "label": None,
                "error": error_msg
            }

    # -------------------------------------------------------------------------
    # Filter Management
    # -------------------------------------------------------------------------
    
    def list_filters(self, user_id: str = 'me') -> Dict[str, Any]:
        """List all filters in the user's settings.
        
        Args:
            user_id: User's email address or 'me'
            
        Returns:
            Dict containing filters and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "filters": [],
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Listing filters for user {user_id}")
            
            # Get filter list
            response = self.service.users().settings().filters().list(userId=user_id).execute()
            
            filters = response.get('filter', [])
            logger.info(f"Found {len(filters)} filters")
            
            return {
                "filters": filters,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error listing filters: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "filters": [],
                "error": error_msg
            }
    
    def create_filter(self, criteria: Dict[str, Any], action: Dict[str, Any], 
                     user_id: str = 'me') -> Dict[str, Any]:
        """Create a new filter in the user's settings.
        
        Args:
            criteria: Filter criteria (from, to, subject, query, etc.)
            action: Action to take (add/remove labels, forward, etc.)
            user_id: User's email address or 'me'
            
        Returns:
            Dict containing created filter data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "filter": None,
                    "error": "Failed to authenticate with Gmail"
                }
        
        try:
            logger.debug(f"Creating filter for user {user_id}")
            
            # Create filter body
            filter_body = {
                'criteria': criteria,
                'action': action
            }
            
            # Create the filter
            created_filter = self.service.users().settings().filters().create(
                userId=user_id,
                body=filter_body
            ).execute()
            
            logger.info(f"Filter created successfully with ID: {created_filter.get('id')}")
            
            return {
                "filter": created_filter,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error creating filter: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "filter": None,
                "error": error_msg
            }

# Create a default helper instance
gmail_helper = GmailHelper(
    # Added gmail.compose scope for draft operations and gmail.metadata for history
    scopes=[
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/gmail.metadata',
        'https://www.googleapis.com/auth/gmail.modify'
    ],
    token_path=Path(__file__).parent / 'token.json',
    credentials_path=Path(__file__).parent / 'credentials.json'
)

def ensure_authenticated() -> Dict[str, Any]:
    """
    Ensure Gmail API authentication is valid and ready to use.
    This function can be called directly before starting the server
    to ensure authentication is ready.
    
    Returns:
        Dict with authentication status and any error message
    """
    try:
        logger.info("Checking Gmail API authentication status")
        
        # Try to authenticate
        success = gmail_helper.authenticate()
        
        if success:
            # Get user profile to verify authentication
            profile_result = gmail_helper.get_profile()
            
            if profile_result["error"]:
                return {
                    "authenticated": False,
                    "error": profile_result["error"],
                    "message": "Authentication validated but profile retrieval failed"
                }
            
            email = profile_result["profile"].get("emailAddress", "unknown")
            return {
                "authenticated": True,
                "error": None,
                "message": f"Successfully authenticated as {email}",
                "email": email
            }
        else:
            return {
                "authenticated": False,
                "error": "Authentication failed",
                "message": "Failed to authenticate with Gmail API" 
            }
            
    except Exception as e:
        error_msg = f"Authentication error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "authenticated": False,
            "error": error_msg,
            "message": "Unexpected error during authentication check"
        } 