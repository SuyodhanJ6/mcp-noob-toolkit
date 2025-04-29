#!/usr/bin/env python
"""
Helper functions for Google Drive MCP tools
"""

import os
import io
import logging
from typing import Optional, Dict, Any, List, BinaryIO
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request as GoogleRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger('gdrive_helper')

class GoogleDriveHelper:
    """Helper class for Google Drive operations"""
    
    # MIME types for Google Workspace documents
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
    
    # Export formats for Google Workspace documents
    EXPORT_FORMATS = {
        'application/vnd.google-apps.document': {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain',
            'html': 'text/html',
            'odt': 'application/vnd.oasis.opendocument.text',
            'rtf': 'application/rtf'
        },
        'application/vnd.google-apps.spreadsheet': {
            'pdf': 'application/pdf',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'csv': 'text/csv',
            'ods': 'application/vnd.oasis.opendocument.spreadsheet'
        },
        'application/vnd.google-apps.presentation': {
            'pdf': 'application/pdf',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'txt': 'text/plain',
            'odp': 'application/vnd.oasis.opendocument.presentation'
        }
    }
    
    def __init__(self, scopes: List[str], token_path: Path, credentials_path: Path):
        """Initialize Google Drive helper.
        
        Args:
            scopes: List of Google Drive API scopes
            token_path: Path to token.json
            credentials_path: Path to credentials.json
        """
        self.scopes = scopes
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.service = None
    
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API.
        
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
                        print(" GOOGLE DRIVE AUTHENTICATION REQUIRED ".center(80, "="))
                        print("="*80)
                        print("\nThis application needs to access your Google Drive account.")
                        print("1. A browser window will open shortly.")
                        print("2. Select your Google account and grant the requested permissions.")
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

            # Store credentials for use by other services
            self.credentials = creds
            
            # Build Google Drive service
            self.service = build('drive', 'v3', credentials=creds)
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def list_files(self, query: str = "", max_results: int = 10) -> Dict[str, Any]:
        """List files in Google Drive.
        
        Args:
            query: Google Drive search query
            max_results: Maximum number of results to return
            
        Returns:
            Dict containing files and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "files": [],
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            # Get files list
            response = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size, parents)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = response.get('files', [])
            if not files:
                return {
                    "files": [],
                    "error": f"No files found matching query: {query}"
                }
            
            logger.info(f"Successfully retrieved {len(files)} files")
            return {
                "files": files,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return {
                "files": [],
                "error": f"Error listing files: {str(e)}"
            }
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get detailed metadata of a specific file.
        
        Args:
            file_id: ID of the file
            
        Returns:
            Dict containing file metadata and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "metadata": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, createdTime, modifiedTime, size, parents, description"
            ).execute()
            
            return {
                "metadata": file_metadata,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return {
                "metadata": None,
                "error": f"Error getting file metadata: {str(e)}"
            }
    
    def download_file(self, file_id: str, export_format: str = None) -> Dict[str, Any]:
        """Download a file from Google Drive.
        
        Args:
            file_id: ID of the file to download
            export_format: Format to export Google Workspace documents to
            
        Returns:
            Dict containing file content and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "content": None,
                    "mime_type": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            # Get file metadata to check if it's a Google Workspace document
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="name, mimeType"
            ).execute()
            
            file_name = file_metadata.get('name', 'file')
            mime_type = file_metadata.get('mimeType', '')
            
            # Handle Google Workspace documents differently
            if mime_type.startswith('application/vnd.google-apps'):
                if not export_format:
                    # Default export formats for different document types
                    if mime_type == 'application/vnd.google-apps.document':
                        export_format = 'pdf'
                    elif mime_type == 'application/vnd.google-apps.spreadsheet':
                        export_format = 'xlsx'
                    elif mime_type == 'application/vnd.google-apps.presentation':
                        export_format = 'pptx'
                    else:
                        export_format = 'pdf'  # Default to PDF for other types
                
                # Get export MIME type
                if mime_type in self.EXPORT_FORMATS and export_format in self.EXPORT_FORMATS[mime_type]:
                    export_mime_type = self.EXPORT_FORMATS[mime_type][export_format]
                else:
                    return {
                        "content": None,
                        "mime_type": None,
                        "error": f"Export format '{export_format}' not supported for this document type"
                    }
                
                # Download as the specified format
                response = self.service.files().export(
                    fileId=file_id,
                    mimeType=export_mime_type
                ).execute()
                
                return {
                    "content": response,
                    "mime_type": export_mime_type,
                    "file_name": f"{file_name}.{export_format}",
                    "error": None
                }
            else:
                # Regular file download
                response = self.service.files().get_media(fileId=file_id).execute()
                
                return {
                    "content": response,
                    "mime_type": mime_type,
                    "file_name": file_name,
                    "error": None
                }
        
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return {
                "content": None,
                "mime_type": None,
                "error": f"Error downloading file: {str(e)}"
            }
    
    def create_folder(self, name: str, parent_id: str = None) -> Dict[str, Any]:
        """Create a new folder in Google Drive.
        
        Args:
            name: Folder name
            parent_id: ID of parent folder (optional)
            
        Returns:
            Dict containing folder metadata and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "folder": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            file_metadata = {
                'name': name,
                'mimeType': self.MIME_TYPES['folder']
            }
            
            # Add parent folder if specified
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, name, mimeType, createdTime, parents'
            ).execute()
            
            logger.info(f"Folder created: {folder.get('name')} (ID: {folder.get('id')})")
            return {
                "folder": folder,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return {
                "folder": None,
                "error": f"Error creating folder: {str(e)}"
            }
    
    def upload_file(self, file_path: str, name: str = None, parent_id: str = None,
                   mime_type: str = None, convert: bool = False) -> Dict[str, Any]:
        """Upload a file to Google Drive.
        
        Args:
            file_path: Path to the file to upload
            name: Name to give the file in Drive (optional)
            parent_id: ID of parent folder (optional)
            mime_type: MIME type of the file (optional)
            convert: Whether to convert to Google format (optional)
            
        Returns:
            Dict containing uploaded file metadata and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "file": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            # If no name is provided, use the filename from the path
            if not name:
                name = os.path.basename(file_path)
            
            file_metadata = {'name': name}
            
            # Add parent folder if specified
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            # Handle conversion to Google format if requested
            if convert:
                # Determine target Google format based on file extension
                extension = os.path.splitext(file_path)[1].lower()
                if extension in ['.doc', '.docx', '.txt', '.rtf', '.odt']:
                    file_metadata['mimeType'] = self.MIME_TYPES['document']
                elif extension in ['.xls', '.xlsx', '.csv', '.ods']:
                    file_metadata['mimeType'] = self.MIME_TYPES['spreadsheet']
                elif extension in ['.ppt', '.pptx', '.odp']:
                    file_metadata['mimeType'] = self.MIME_TYPES['presentation']
            
            # Create media upload object
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload the file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, createdTime, parents'
            ).execute()
            
            logger.info(f"File uploaded: {file.get('name')} (ID: {file.get('id')})")
            return {
                "file": file,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return {
                "file": None,
                "error": f"Error uploading file: {str(e)}"
            }
    
    def create_document(self, name: str, content: str = None, parent_id: str = None) -> Dict[str, Any]:
        """Create a new Google Docs document.
        
        Args:
            name: Document name
            content: Initial content (optional)
            parent_id: ID of parent folder (optional)
            
        Returns:
            Dict containing document metadata and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "document": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            file_metadata = {
                'name': name,
                'mimeType': self.MIME_TYPES['document']
            }
            
            # Add parent folder if specified
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            # Create empty document
            document = self.service.files().create(
                body=file_metadata,
                fields='id, name, mimeType, createdTime, parents'
            ).execute()
            
            # If content is provided, we need to use the Docs API to add content
            if content:
                # This would require additional Google Docs API
                # For simplicity, we'll skip this part
                pass
            
            logger.info(f"Document created: {document.get('name')} (ID: {document.get('id')})")
            return {
                "document": document,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            return {
                "document": None,
                "error": f"Error creating document: {str(e)}"
            }
    
    def create_spreadsheet(self, name: str, parent_id: str = None) -> Dict[str, Any]:
        """Create a new Google Sheets spreadsheet.
        
        Args:
            name: Spreadsheet name
            parent_id: ID of parent folder (optional)
            
        Returns:
            Dict containing spreadsheet metadata and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "spreadsheet": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            file_metadata = {
                'name': name,
                'mimeType': self.MIME_TYPES['spreadsheet']
            }
            
            # Add parent folder if specified
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            # Create empty spreadsheet
            spreadsheet = self.service.files().create(
                body=file_metadata,
                fields='id, name, mimeType, createdTime, parents'
            ).execute()
            
            logger.info(f"Spreadsheet created: {spreadsheet.get('name')} (ID: {spreadsheet.get('id')})")
            return {
                "spreadsheet": spreadsheet,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error creating spreadsheet: {e}")
            return {
                "spreadsheet": None,
                "error": f"Error creating spreadsheet: {str(e)}"
            }
    
    def create_presentation(self, name: str, parent_id: str = None) -> Dict[str, Any]:
        """Create a new Google Slides presentation.
        
        Args:
            name: Presentation name
            parent_id: ID of parent folder (optional)
            
        Returns:
            Dict containing presentation metadata and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "presentation": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            file_metadata = {
                'name': name,
                'mimeType': self.MIME_TYPES['presentation']
            }
            
            # Add parent folder if specified
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            # Create empty presentation
            presentation = self.service.files().create(
                body=file_metadata,
                fields='id, name, mimeType, createdTime, parents'
            ).execute()
            
            logger.info(f"Presentation created: {presentation.get('name')} (ID: {presentation.get('id')})")
            return {
                "presentation": presentation,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error creating presentation: {e}")
            return {
                "presentation": None,
                "error": f"Error creating presentation: {str(e)}"
            }
    
    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """Delete a file from Google Drive.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            Dict indicating success or failure
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "success": False,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            
            logger.info(f"File deleted (ID: {file_id})")
            return {
                "success": True,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return {
                "success": False,
                "error": f"Error deleting file: {str(e)}"
            }
    
    def update_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update metadata of a file.
        
        Args:
            file_id: ID of the file to update
            metadata: Dict containing metadata fields to update
            
        Returns:
            Dict containing updated file metadata and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "file": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            updated_file = self.service.files().update(
                fileId=file_id,
                body=metadata,
                fields='id, name, mimeType, createdTime, modifiedTime, parents, description'
            ).execute()
            
            logger.info(f"File updated: {updated_file.get('name')} (ID: {updated_file.get('id')})")
            return {
                "file": updated_file,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error updating file metadata: {e}")
            return {
                "file": None,
                "error": f"Error updating file metadata: {str(e)}"
            }
    
    def move_file(self, file_id: str, new_parent_id: str, remove_parents: bool = True) -> Dict[str, Any]:
        """Move a file to a different folder.
        
        Args:
            file_id: ID of the file to move
            new_parent_id: ID of the destination folder
            remove_parents: Whether to remove existing parents (default True)
            
        Returns:
            Dict containing updated file metadata and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "file": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            # Get current parents
            file = self.service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            
            # Move file to new parent
            updated_file = self.service.files().update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=previous_parents if remove_parents else None,
                fields='id, name, parents'
            ).execute()
            
            logger.info(f"File moved: {updated_file.get('name')} (ID: {updated_file.get('id')})")
            return {
                "file": updated_file,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return {
                "file": None,
                "error": f"Error moving file: {str(e)}"
            }
    
    def share_file(self, file_id: str, email: str, role: str = 'reader', 
                  type: str = 'user', notify: bool = False) -> Dict[str, Any]:
        """Share a file with another user.
        
        Args:
            file_id: ID of the file to share
            email: Email address of the user to share with
            role: Permission role ('reader', 'writer', 'commenter', 'owner')
            type: Permission type ('user', 'group', 'domain', 'anyone')
            notify: Whether to send notification email
            
        Returns:
            Dict containing permission data and any error
        """
        if not self.service:
            if not self.authenticate():
                return {
                    "permission": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        try:
            permission = {
                'type': type,
                'role': role
            }
            
            # Add email for user, group, domain types
            if type in ['user', 'group']:
                permission['emailAddress'] = email
            elif type == 'domain':
                permission['domain'] = email
                
            # Create permission
            created_permission = self.service.permissions().create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=notify,
                fields='id, type, role, emailAddress'
            ).execute()
            
            logger.info(f"File shared: {file_id} with {email}")
            return {
                "permission": created_permission,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error sharing file: {e}")
            return {
                "permission": None,
                "error": f"Error sharing file: {str(e)}"
            }

# Create a default helper instance
drive_helper = GoogleDriveHelper(
    scopes=[
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.appdata',
        'https://www.googleapis.com/auth/drive.metadata',
        # Add more specific scopes for document editing
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/presentations'
    ],
    token_path=Path(__file__).parent / 'token.json',
    credentials_path=Path(__file__).parent / 'credentials.json'
)

# Advanced Document Editing Operations
def get_document_content(doc_id: str) -> Dict[str, Any]:
    """
    Get the content of a Google Docs document.
    
    Args:
        doc_id: ID of the document to get content from
        
    Returns:
        Dict containing document content and any error
    """
    try:
        # Check if drive helper is authenticated
        if not drive_helper.service:
            if not drive_helper.authenticate():
                return {
                    "content": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        # Need to use the Google Docs API for this
        docs_service = build('docs', 'v1', credentials=drive_helper.credentials)
        
        # Get the document content
        document = docs_service.documents().get(documentId=doc_id).execute()
        
        logger.info(f"Retrieved content from document: {document.get('title')}")
        return {
            "content": document,
            "error": None
        }
    except HttpError as e:
        # Handle the case where Google Docs API is not enabled
        if e.resp.status == 403 and "PERMISSION_DENIED" in str(e) and "SERVICE_DISABLED" in str(e):
            error_msg = "Google Docs API is not enabled in your Google Cloud project. Please enable it at: " \
                        "https://console.developers.google.com/apis/api/docs.googleapis.com/overview"
            logger.error(f"API not enabled: {error_msg}")
            return {
                "content": None,
                "error": error_msg
            }
        error_msg = f"Error getting document content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "content": None,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error getting document content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "content": None,
            "error": error_msg
        }

def update_document_content(doc_id: str, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Update the content of a Google Docs document.
    
    Args:
        doc_id: ID of the document to update
        requests: List of change requests to apply to the document
        
    Returns:
        Dict containing update result and any error
    """
    try:
        # Check if drive helper is authenticated
        if not drive_helper.service:
            if not drive_helper.authenticate():
                return {
                    "result": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        # Need to use the Google Docs API for this
        docs_service = build('docs', 'v1', credentials=drive_helper.credentials)
        
        # Apply the updates to the document
        result = docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        
        logger.info(f"Updated document with ID: {doc_id}")
        return {
            "result": result,
            "error": None
        }
    except HttpError as e:
        # Handle the case where Google Docs API is not enabled
        if e.resp.status == 403 and "PERMISSION_DENIED" in str(e) and "SERVICE_DISABLED" in str(e):
            error_msg = "Google Docs API is not enabled in your Google Cloud project. Please enable it at: " \
                        "https://console.developers.google.com/apis/api/docs.googleapis.com/overview"
            logger.error(f"API not enabled: {error_msg}")
            return {
                "result": None,
                "error": error_msg
            }
        error_msg = f"Error updating document content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "result": None,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error updating document content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "result": None,
            "error": error_msg
        }

def get_spreadsheet_content(sheet_id: str) -> Dict[str, Any]:
    """
    Get the content of a Google Sheets spreadsheet.
    
    Args:
        sheet_id: ID of the spreadsheet to get content from
        
    Returns:
        Dict containing spreadsheet content and any error
    """
    try:
        # Check if drive helper is authenticated
        if not drive_helper.service:
            if not drive_helper.authenticate():
                return {
                    "content": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        # Need to use the Google Sheets API for this
        sheets_service = build('sheets', 'v4', credentials=drive_helper.credentials)
        
        # Get spreadsheet metadata including sheet names
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        
        # Get data from all sheets
        sheet_data = {}
        for sheet in spreadsheet.get('sheets', []):
            sheet_name = sheet['properties']['title']
            sheet_id_internal = sheet['properties']['sheetId']
            
            # Get data from this sheet
            range_name = f"{sheet_name}"
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            sheet_data[sheet_name] = result.get('values', [])
        
        logger.info(f"Retrieved content from spreadsheet: {spreadsheet.get('properties', {}).get('title')}")
        return {
            "content": {
                "metadata": spreadsheet,
                "sheets": sheet_data
            },
            "error": None
        }
    except HttpError as e:
        # Handle the case where Google Sheets API is not enabled
        if e.resp.status == 403 and "PERMISSION_DENIED" in str(e) and "SERVICE_DISABLED" in str(e):
            error_msg = "Google Sheets API is not enabled in your Google Cloud project. Please enable it at: " \
                        "https://console.developers.google.com/apis/api/sheets.googleapis.com/overview"
            logger.error(f"API not enabled: {error_msg}")
            return {
                "content": None,
                "error": error_msg
            }
        error_msg = f"Error getting spreadsheet content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "content": None,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error getting spreadsheet content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "content": None,
            "error": error_msg
        }

def update_spreadsheet_content(sheet_id: str, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Update the content of a Google Sheets spreadsheet.
    
    Args:
        sheet_id: ID of the spreadsheet to update
        updates: List of update requests to apply to the spreadsheet
        
    Returns:
        Dict containing update result and any error
    """
    try:
        # Check if drive helper is authenticated
        if not drive_helper.service:
            if not drive_helper.authenticate():
                return {
                    "result": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        # Need to use the Google Sheets API for this
        sheets_service = build('sheets', 'v4', credentials=drive_helper.credentials)
        
        # Apply the batch updates
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={'requests': updates}
        ).execute()
        
        logger.info(f"Updated spreadsheet with ID: {sheet_id}")
        return {
            "result": result,
            "error": None
        }
    except HttpError as e:
        # Handle the case where Google Sheets API is not enabled
        if e.resp.status == 403 and "PERMISSION_DENIED" in str(e) and "SERVICE_DISABLED" in str(e):
            error_msg = "Google Sheets API is not enabled in your Google Cloud project. Please enable it at: " \
                        "https://console.developers.google.com/apis/api/sheets.googleapis.com/overview"
            logger.error(f"API not enabled: {error_msg}")
            return {
                "result": None,
                "error": error_msg
            }
        error_msg = f"Error updating spreadsheet content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "result": None,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error updating spreadsheet content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "result": None,
            "error": error_msg
        }

def update_spreadsheet_values(sheet_id: str, range_name: str, values: List[List], 
                             value_input_option: str = "USER_ENTERED") -> Dict[str, Any]:
    """
    Update cell values in a Google Sheets spreadsheet.
    
    Args:
        sheet_id: ID of the spreadsheet to update
        range_name: Range to update in A1 notation (e.g., "Sheet1!A1:B5")
        values: 2D array of values to set
        value_input_option: How to interpret the input values ("RAW" or "USER_ENTERED")
        
    Returns:
        Dict containing update result and any error
    """
    try:
        # Check if drive helper is authenticated
        if not drive_helper.service:
            if not drive_helper.authenticate():
                return {
                    "result": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        # Need to use the Google Sheets API for this
        sheets_service = build('sheets', 'v4', credentials=drive_helper.credentials)
        
        # Apply the values update
        body = {
            'values': values
        }
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        ).execute()
        
        logger.info(f"Updated spreadsheet values in range {range_name}")
        return {
            "result": result,
            "error": None
        }
    except HttpError as e:
        # Handle the case where Google Sheets API is not enabled
        if e.resp.status == 403 and "PERMISSION_DENIED" in str(e) and "SERVICE_DISABLED" in str(e):
            error_msg = "Google Sheets API is not enabled in your Google Cloud project. Please enable it at: " \
                        "https://console.developers.google.com/apis/api/sheets.googleapis.com/overview"
            logger.error(f"API not enabled: {error_msg}")
            return {
                "result": None,
                "error": error_msg
            }
        error_msg = f"Error updating spreadsheet values: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "result": None,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error updating spreadsheet values: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "result": None,
            "error": error_msg
        }

def get_presentation_content(presentation_id: str) -> Dict[str, Any]:
    """
    Get the content of a Google Slides presentation.
    
    Args:
        presentation_id: ID of the presentation to get content from
        
    Returns:
        Dict containing presentation content and any error
    """
    try:
        # Check if drive helper is authenticated
        if not drive_helper.service:
            if not drive_helper.authenticate():
                return {
                    "content": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        # Need to use the Google Slides API for this
        slides_service = build('slides', 'v1', credentials=drive_helper.credentials)
        
        # Get the presentation content
        presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
        
        logger.info(f"Retrieved content from presentation: {presentation.get('title')}")
        return {
            "content": presentation,
            "error": None
        }
    except HttpError as e:
        # Handle the case where Google Slides API is not enabled
        if e.resp.status == 403 and "PERMISSION_DENIED" in str(e) and "SERVICE_DISABLED" in str(e):
            error_msg = "Google Slides API is not enabled in your Google Cloud project. Please enable it at: " \
                        "https://console.developers.google.com/apis/api/slides.googleapis.com/overview"
            logger.error(f"API not enabled: {error_msg}")
            return {
                "content": None,
                "error": error_msg
            }
        error_msg = f"Error getting presentation content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "content": None,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error getting presentation content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "content": None,
            "error": error_msg
        }

def update_presentation_content(presentation_id: str, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Update the content of a Google Slides presentation.
    
    Args:
        presentation_id: ID of the presentation to update
        requests: List of change requests to apply to the presentation
        
    Returns:
        Dict containing update result and any error
    """
    try:
        # Check if drive helper is authenticated
        if not drive_helper.service:
            if not drive_helper.authenticate():
                return {
                    "result": None,
                    "error": "Failed to authenticate with Google Drive"
                }
        
        # Need to use the Google Slides API for this
        slides_service = build('slides', 'v1', credentials=drive_helper.credentials)
        
        # Apply the updates to the presentation
        result = slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        
        logger.info(f"Updated presentation with ID: {presentation_id}")
        return {
            "result": result,
            "error": None
        }
    except HttpError as e:
        # Handle the case where Google Slides API is not enabled
        if e.resp.status == 403 and "PERMISSION_DENIED" in str(e) and "SERVICE_DISABLED" in str(e):
            error_msg = "Google Slides API is not enabled in your Google Cloud project. Please enable it at: " \
                        "https://console.developers.google.com/apis/api/slides.googleapis.com/overview"
            logger.error(f"API not enabled: {error_msg}")
            return {
                "result": None,
                "error": error_msg
            }
        error_msg = f"Error updating presentation content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "result": None,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error updating presentation content: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "result": None,
            "error": error_msg
        }

def ensure_authenticated() -> Dict[str, Any]:
    """
    Ensure Google Drive API authentication is valid and ready to use.
    This function can be called directly before starting the server
    to ensure authentication is ready.
    
    Returns:
        Dict with authentication status and any error message
    """
    try:
        logger.info("Checking Google Drive API authentication status")
        
        # Try to authenticate
        success = drive_helper.authenticate()
        
        if success:
            # Get user files to verify authentication
            files_result = drive_helper.list_files(max_results=1)
            
            if files_result["error"]:
                return {
                    "authenticated": False,
                    "error": files_result["error"],
                    "message": "Authentication validated but file listing failed"
                }
            
            return {
                "authenticated": True,
                "error": None,
                "message": "Successfully authenticated with Google Drive API"
            }
        else:
            return {
                "authenticated": False,
                "error": "Authentication failed",
                "message": "Failed to authenticate with Google Drive API" 
            }
            
    except Exception as e:
        error_msg = f"Authentication error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "authenticated": False,
            "error": error_msg,
            "message": "Unexpected error during authentication check"
        } 